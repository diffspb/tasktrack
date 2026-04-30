import uuid

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.decision import Solution, SolutionStatus, TaskDecision
from app.models.task import Assignment, AssigneeRole, GlobalStatus, Task
from app.models.user import User
from app.models.workflow import Status, StatusCategory
from app.schemas.task import (
    AssignmentCreate,
    AssignmentRoleUpdate,
    AssignmentTransition,
    TaskCreate,
    TaskUpdate,
)
from app.services.permissions import require_project_access
from app.services.workflow_service import validate_transition


async def create_task(
    session: AsyncSession, project_id: uuid.UUID, data: TaskCreate, user: User
) -> Task:
    await require_project_access(session, project_id, user)

    project = await session.get(
        __import__("app.models.project", fromlist=["Project"]).Project, project_id
    )
    count = await session.scalar(
        select(func.count()).select_from(Task).where(Task.project_id == project_id)
    ) or 0
    key = f"{project.key}-{count + 1}"

    task = Task(
        project_id=project_id,
        workflow_id=data.workflow_id,
        reporter_id=user.id,
        decision_maker_id=data.decision_maker_id,
        key=key,
        title=data.title,
        description=data.description,
        task_type=data.task_type,
        priority=data.priority,
        global_status=GlobalStatus.open,
        due_date=data.due_date,
        allow_multi_accept=data.allow_multi_accept,
    )
    session.add(task)
    await session.commit()
    return await _load_task(session, task.id)


async def get_task(
    session: AsyncSession, task_id: uuid.UUID, user: User
) -> Task:
    task = await _load_task(session, task_id)
    if not task or task.deleted_at is not None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, {"code": "TASK_NOT_FOUND"})
    await require_project_access(session, task.project_id, user)
    return task


async def list_tasks(
    session: AsyncSession, project_id: uuid.UUID, user: User,
    global_status: GlobalStatus | None = None,
) -> list[Task]:
    await require_project_access(session, project_id, user)
    stmt = (
        select(Task)
        .options(selectinload(Task.assignments))
        .where(Task.project_id == project_id, Task.deleted_at.is_(None))
    )
    if global_status:
        stmt = stmt.where(Task.global_status == global_status)
    return list((await session.scalars(stmt)).all())


async def list_my_tasks(session: AsyncSession, user: User) -> list[Task]:
    assigned_task_ids = select(Assignment.task_id).where(Assignment.user_id == user.id)
    stmt = (
        select(Task)
        .options(selectinload(Task.assignments))
        .where(Task.id.in_(assigned_task_ids), Task.deleted_at.is_(None))
    )
    return list((await session.scalars(stmt)).all())


async def update_task(
    session: AsyncSession, task_id: uuid.UUID, data: TaskUpdate, user: User
) -> Task:
    task = await get_task(session, task_id, user)

    if data.version != task.version:
        raise HTTPException(status.HTTP_409_CONFLICT, {"code": "VERSION_CONFLICT"})

    if data.title is not None:
        task.title = data.title
    if data.description is not None:
        task.description = data.description
    if data.priority is not None:
        task.priority = data.priority
    if data.decision_maker_id is not None:
        task.decision_maker_id = data.decision_maker_id
    if data.due_date is not None:
        task.due_date = data.due_date
    if data.allow_multi_accept is not None:
        task.allow_multi_accept = data.allow_multi_accept
    task.version += 1

    await session.commit()
    return await _load_task(session, task.id)


async def delete_task(
    session: AsyncSession, task_id: uuid.UUID, user: User
) -> None:
    from datetime import UTC, datetime
    task = await get_task(session, task_id, user)
    task.deleted_at = datetime.now(UTC)
    await session.commit()


async def assign_user(
    session: AsyncSession, task_id: uuid.UUID, data: AssignmentCreate, user: User
) -> Assignment:
    task = await get_task(session, task_id, user)

    initial_status = await session.scalar(
        select(Status).where(
            Status.workflow_id == task.workflow_id,
            Status.is_default == True,  # noqa: E712
        )
    )
    if not initial_status:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            {"code": "WORKFLOW_NO_DEFAULT_STATUS"},
        )

    assignment = Assignment(
        task_id=task_id,
        user_id=data.user_id,
        role=data.role,
        current_status_id=initial_status.id,
    )
    session.add(assignment)
    await session.flush()

    await _recalculate_global_status(session, task)
    await session.commit()
    await session.refresh(assignment)
    return assignment


async def transition_assignment_status(
    session: AsyncSession,
    assignment_id: uuid.UUID,
    data: AssignmentTransition,
    user: User,
) -> Assignment:
    assignment = await _get_assignment_or_404(session, assignment_id)
    task = await get_task(session, assignment.task_id, user)

    if assignment.user_id != user.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, {"code": "PERMISSION_DENIED"})

    if not await validate_transition(
        session, task.workflow_id, assignment.current_status_id, data.status_id
    ):
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            {"code": "WORKFLOW_TRANSITION_NOT_ALLOWED"},
        )

    target = await session.get(Status, data.status_id)
    if target and target.category == StatusCategory.final and data.resolution_id is None:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            {"code": "RESOLUTION_REQUIRED"},
        )

    assignment.current_status_id = data.status_id
    assignment.resolution_id = data.resolution_id

    await _recalculate_global_status(session, task)
    await session.commit()
    await session.refresh(assignment)
    return assignment


async def update_assignment_role(
    session: AsyncSession,
    assignment_id: uuid.UUID,
    data: AssignmentRoleUpdate,
    user: User,
) -> Assignment:
    assignment = await _get_assignment_or_404(session, assignment_id)
    task = await get_task(session, assignment.task_id, user)

    assignment.role = data.role
    await _recalculate_global_status(session, task)
    await session.commit()
    await session.refresh(assignment)
    return assignment


async def remove_assignment(
    session: AsyncSession, assignment_id: uuid.UUID, user: User
) -> None:
    assignment = await _get_assignment_or_404(session, assignment_id)
    task = await get_task(session, assignment.task_id, user)
    await session.delete(assignment)
    await _recalculate_global_status(session, task)
    await session.commit()


# --- Internal helpers ---

async def _load_task(session: AsyncSession, task_id: uuid.UUID) -> Task | None:
    return await session.scalar(
        select(Task)
        .options(selectinload(Task.assignments))
        .where(Task.id == task_id)
    )


async def _get_assignment_or_404(
    session: AsyncSession, assignment_id: uuid.UUID
) -> Assignment:
    a = await session.get(Assignment, assignment_id)
    if not a:
        raise HTTPException(status.HTTP_404_NOT_FOUND, {"code": "ASSIGNMENT_NOT_FOUND"})
    return a


async def _recalculate_global_status(session: AsyncSession, task: Task) -> None:
    """
    Single-lead path: personal-status-based (open → in_progress → closed).
    Multi-lead path: Solution-based — workflow personal status alone never
    moves the task to awaiting_decision; that transition is owned by
    decision_service.submit_solution. Same for in_revision / decided.
    """
    decided = await session.scalar(
        select(TaskDecision).where(TaskDecision.task_id == task.id)
    )
    if decided is not None and task.global_status in (
        GlobalStatus.decided, GlobalStatus.closed,
    ):
        return

    leads = list((await session.scalars(
        select(Assignment).where(
            Assignment.task_id == task.id,
            Assignment.role == AssigneeRole.lead,
        )
    )).all())

    if not leads:
        task.global_status = GlobalStatus.open
        return

    if len(leads) == 1:
        final_ids = set((await session.scalars(
            select(Status.id).where(
                Status.workflow_id == task.workflow_id,
                Status.category == StatusCategory.final,
            )
        )).all())
        lead = leads[0]
        if lead.current_status_id in final_ids:
            task.global_status = GlobalStatus.closed
        else:
            task.global_status = GlobalStatus.in_progress
        return

    # Multi-lead: Solution-based.
    solutions = list((await session.scalars(
        select(Solution).where(
            Solution.assignment_id.in_([a.id for a in leads])
        )
    )).all())
    by_assignment = {s.assignment_id: s for s in solutions}

    if any(
        (s := by_assignment.get(a.id)) is not None
        and s.status == SolutionStatus.revision_requested
        for a in leads
    ):
        task.global_status = GlobalStatus.in_revision
        return

    all_submitted = all(
        (s := by_assignment.get(a.id)) is not None
        and s.status == SolutionStatus.submitted
        for a in leads
    )
    if all_submitted:
        task.global_status = GlobalStatus.awaiting_decision
    else:
        task.global_status = GlobalStatus.in_progress
