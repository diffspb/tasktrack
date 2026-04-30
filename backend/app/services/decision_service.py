"""
Decision Process service: Solution lifecycle, DecisionCriteria,
TaskDecision, revision cycle.

Concurrency: every transition that may flip global_status acquires a row
lock on Task via SELECT FOR UPDATE; the lock is released at commit.
"""
import uuid
from datetime import UTC, datetime

from fastapi import HTTPException, status as http_status
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.decision import (
    DecisionCriteria,
    Solution,
    SolutionStatus,
    TaskDecision,
)
from app.models.task import Assignment, AssigneeRole, GlobalStatus, Task
from app.models.user import User
from app.schemas.decision import (
    DecisionCreate,
    DecisionCriteriaReplace,
    SolutionCreate,
    SolutionUpdate,
)
from app.services.permissions import require_project_access
from app.services.task_service import _recalculate_global_status


# --- Helpers ----------------------------------------------------------------

async def _lock_task(session: AsyncSession, task_id: uuid.UUID) -> Task:
    task = await session.scalar(
        select(Task).where(Task.id == task_id).with_for_update()
    )
    if not task or task.deleted_at is not None:
        raise HTTPException(http_status.HTTP_404_NOT_FOUND, {"code": "TASK_NOT_FOUND"})
    return task


async def _get_assignment(session: AsyncSession, assignment_id: uuid.UUID) -> Assignment:
    a = await session.get(Assignment, assignment_id)
    if not a:
        raise HTTPException(
            http_status.HTTP_404_NOT_FOUND, {"code": "ASSIGNMENT_NOT_FOUND"}
        )
    return a


async def _get_solution(session: AsyncSession, solution_id: uuid.UUID) -> Solution:
    sol = await session.get(Solution, solution_id)
    if not sol:
        raise HTTPException(
            http_status.HTTP_404_NOT_FOUND, {"code": "SOLUTION_NOT_FOUND"}
        )
    return sol


def _require_lead(assignment: Assignment) -> None:
    if assignment.role != AssigneeRole.lead:
        raise HTTPException(
            http_status.HTTP_403_FORBIDDEN, {"code": "PERMISSION_DENIED"}
        )


def _require_owner(assignment: Assignment, user: User) -> None:
    if assignment.user_id != user.id:
        raise HTTPException(
            http_status.HTTP_403_FORBIDDEN, {"code": "PERMISSION_DENIED"}
        )


def _require_decision_maker(task: Task, user: User) -> None:
    if task.decision_maker_id != user.id:
        raise HTTPException(
            http_status.HTTP_403_FORBIDDEN, {"code": "PERMISSION_DENIED"}
        )


async def _lock_decision_criteria(session: AsyncSession, task_id: uuid.UUID) -> None:
    await session.execute(
        update(DecisionCriteria)
        .where(DecisionCriteria.task_id == task_id)
        .values(is_locked=True)
    )


# --- Solution ---------------------------------------------------------------

async def create_solution(
    session: AsyncSession,
    assignment_id: uuid.UUID,
    data: SolutionCreate,
    user: User,
) -> Solution:
    assignment = await _get_assignment(session, assignment_id)
    task = await session.get(Task, assignment.task_id)
    await require_project_access(session, task.project_id, user)

    _require_lead(assignment)
    _require_owner(assignment, user)

    existing = await session.scalar(
        select(Solution).where(Solution.assignment_id == assignment_id)
    )
    if existing:
        raise HTTPException(
            http_status.HTTP_400_BAD_REQUEST,
            {"code": "SOLUTION_ALREADY_EXISTS"},
        )

    sol = Solution(
        assignment_id=assignment_id,
        content=data.content,
        status=SolutionStatus.draft,
    )
    session.add(sol)
    await session.commit()
    await session.refresh(sol)
    return sol


async def get_solution_by_assignment(
    session: AsyncSession, assignment_id: uuid.UUID, user: User
) -> Solution:
    assignment = await _get_assignment(session, assignment_id)
    task = await session.get(Task, assignment.task_id)
    await require_project_access(session, task.project_id, user)

    sol = await session.scalar(
        select(Solution).where(Solution.assignment_id == assignment_id)
    )
    if not sol:
        raise HTTPException(
            http_status.HTTP_404_NOT_FOUND, {"code": "SOLUTION_NOT_FOUND"}
        )

    await _check_solution_visibility(session, task, assignment, user)
    return sol


async def update_solution(
    session: AsyncSession,
    solution_id: uuid.UUID,
    data: SolutionUpdate,
    user: User,
) -> Solution:
    sol = await _get_solution(session, solution_id)
    assignment = await _get_assignment(session, sol.assignment_id)
    _require_owner(assignment, user)

    if sol.status not in (SolutionStatus.draft, SolutionStatus.revision_requested):
        raise HTTPException(
            http_status.HTTP_400_BAD_REQUEST,
            {"code": "SOLUTION_LOCKED"},
        )

    sol.content = data.content
    await session.commit()
    await session.refresh(sol)
    return sol


async def submit_solution(
    session: AsyncSession, solution_id: uuid.UUID, user: User
) -> tuple[Solution, GlobalStatus | None]:
    """
    draft|revision_requested → submitted.
    Triggers global_status recalculation under SELECT FOR UPDATE.
    Returns (solution, transitioned_to or None).
    """
    sol = await _get_solution(session, solution_id)
    assignment = await _get_assignment(session, sol.assignment_id)
    _require_owner(assignment, user)
    _require_lead(assignment)

    task = await _lock_task(session, assignment.task_id)
    if task.global_status in (GlobalStatus.decided, GlobalStatus.closed):
        raise HTTPException(
            http_status.HTTP_400_BAD_REQUEST,
            {"code": "CANNOT_MODIFY_DECIDED_TASK"},
        )

    if sol.status == SolutionStatus.submitted:
        raise HTTPException(
            http_status.HTTP_400_BAD_REQUEST,
            {"code": "SOLUTION_ALREADY_SUBMITTED"},
        )
    if sol.status == SolutionStatus.accepted:
        raise HTTPException(
            http_status.HTTP_400_BAD_REQUEST,
            {"code": "SOLUTION_ALREADY_SUBMITTED"},
        )

    sol.status = SolutionStatus.submitted
    sol.submitted_at = datetime.now(UTC)
    sol.revision_comment = None

    await _lock_decision_criteria(session, task.id)

    before = task.global_status
    await _recalculate_global_status(session, task)
    transitioned = task.global_status if task.global_status != before else None

    await session.commit()
    await session.refresh(sol)
    return sol, transitioned


async def withdraw_solution(
    session: AsyncSession, solution_id: uuid.UUID, user: User
) -> tuple[Solution, GlobalStatus | None]:
    """submitted → draft. Disallowed in revision_requested."""
    sol = await _get_solution(session, solution_id)
    assignment = await _get_assignment(session, sol.assignment_id)
    _require_owner(assignment, user)

    if sol.status == SolutionStatus.revision_requested:
        raise HTTPException(
            http_status.HTTP_400_BAD_REQUEST,
            {"code": "SOLUTION_IN_REVISION"},
        )
    if sol.status != SolutionStatus.submitted:
        raise HTTPException(
            http_status.HTTP_400_BAD_REQUEST,
            {"code": "SOLUTION_NOT_SUBMITTED"},
        )

    task = await _lock_task(session, assignment.task_id)
    if task.global_status in (GlobalStatus.decided, GlobalStatus.closed):
        raise HTTPException(
            http_status.HTTP_400_BAD_REQUEST,
            {"code": "CANNOT_MODIFY_DECIDED_TASK"},
        )

    sol.status = SolutionStatus.draft
    sol.submitted_at = None

    before = task.global_status
    await _recalculate_global_status(session, task)
    transitioned = task.global_status if task.global_status != before else None

    await session.commit()
    await session.refresh(sol)
    return sol, transitioned


async def request_revision(
    session: AsyncSession,
    solution_id: uuid.UUID,
    feedback: str,
    user: User,
) -> tuple[Solution, GlobalStatus | None]:
    sol = await _get_solution(session, solution_id)
    assignment = await _get_assignment(session, sol.assignment_id)
    task = await _lock_task(session, assignment.task_id)
    _require_decision_maker(task, user)

    if task.global_status not in (
        GlobalStatus.awaiting_decision, GlobalStatus.in_revision,
    ):
        raise HTTPException(
            http_status.HTTP_400_BAD_REQUEST,
            {"code": "TASK_NOT_AWAITING_DECISION"},
        )
    if sol.status != SolutionStatus.submitted:
        raise HTTPException(
            http_status.HTTP_400_BAD_REQUEST,
            {"code": "SOLUTION_NOT_SUBMITTED"},
        )

    sol.status = SolutionStatus.revision_requested
    sol.revision_comment = feedback

    before = task.global_status
    await _recalculate_global_status(session, task)
    transitioned = task.global_status if task.global_status != before else None

    await session.commit()
    await session.refresh(sol)
    return sol, transitioned


async def list_task_solutions(
    session: AsyncSession, task_id: uuid.UUID, user: User
) -> list[Solution]:
    task = await session.get(Task, task_id)
    if not task or task.deleted_at is not None:
        raise HTTPException(http_status.HTTP_404_NOT_FOUND, {"code": "TASK_NOT_FOUND"})
    await require_project_access(session, task.project_id, user)

    # Consultants see nothing until Decision is made.
    my_assignment = await session.scalar(
        select(Assignment).where(
            Assignment.task_id == task_id,
            Assignment.user_id == user.id,
        )
    )
    if my_assignment and my_assignment.role == AssigneeRole.consultant:
        decision = await session.scalar(
            select(TaskDecision).where(TaskDecision.task_id == task_id)
        )
        if decision is None:
            raise HTTPException(
                http_status.HTTP_403_FORBIDDEN, {"code": "PERMISSION_DENIED"}
            )

    rows = await session.scalars(
        select(Solution)
        .join(Assignment, Solution.assignment_id == Assignment.id)
        .where(Assignment.task_id == task_id)
    )
    return list(rows.all())


async def _check_solution_visibility(
    session: AsyncSession, task: Task, assignment: Assignment, user: User,
) -> None:
    if assignment.user_id == user.id:
        return
    my = await session.scalar(
        select(Assignment).where(
            Assignment.task_id == task.id,
            Assignment.user_id == user.id,
        )
    )
    if my and my.role == AssigneeRole.consultant:
        decision = await session.scalar(
            select(TaskDecision).where(TaskDecision.task_id == task.id)
        )
        if decision is None:
            raise HTTPException(
                http_status.HTTP_403_FORBIDDEN, {"code": "PERMISSION_DENIED"}
            )


# --- Decision criteria ------------------------------------------------------

async def list_criteria(
    session: AsyncSession, task_id: uuid.UUID, user: User
) -> list[DecisionCriteria]:
    task = await session.get(Task, task_id)
    if not task or task.deleted_at is not None:
        raise HTTPException(http_status.HTTP_404_NOT_FOUND, {"code": "TASK_NOT_FOUND"})
    await require_project_access(session, task.project_id, user)
    rows = await session.scalars(
        select(DecisionCriteria)
        .where(DecisionCriteria.task_id == task_id)
        .order_by(DecisionCriteria.position)
    )
    return list(rows.all())


async def replace_criteria(
    session: AsyncSession,
    task_id: uuid.UUID,
    data: DecisionCriteriaReplace,
    user: User,
) -> list[DecisionCriteria]:
    task = await session.get(Task, task_id)
    if not task or task.deleted_at is not None:
        raise HTTPException(http_status.HTTP_404_NOT_FOUND, {"code": "TASK_NOT_FOUND"})
    await require_project_access(session, task.project_id, user)

    existing = list((await session.scalars(
        select(DecisionCriteria).where(DecisionCriteria.task_id == task_id)
    )).all())
    if any(c.is_locked for c in existing):
        raise HTTPException(
            http_status.HTTP_400_BAD_REQUEST,
            {"code": "CRITERIA_LOCKED"},
        )

    for c in existing:
        await session.delete(c)
    await session.flush()

    new_rows = [
        DecisionCriteria(
            task_id=task_id,
            description=item.description,
            position=item.position,
        )
        for item in data.items
    ]
    session.add_all(new_rows)
    await session.commit()
    return await list_criteria(session, task_id, user)


# --- Decision ---------------------------------------------------------------

async def make_decision(
    session: AsyncSession,
    task_id: uuid.UUID,
    data: DecisionCreate,
    user: User,
) -> TaskDecision:
    task = await _lock_task(session, task_id)
    _require_decision_maker(task, user)

    existing = await session.scalar(
        select(TaskDecision).where(TaskDecision.task_id == task_id)
    )
    if existing:
        raise HTTPException(
            http_status.HTTP_409_CONFLICT,
            {"code": "DECISION_ALREADY_MADE"},
        )

    if task.global_status not in (
        GlobalStatus.awaiting_decision, GlobalStatus.in_revision,
    ):
        raise HTTPException(
            http_status.HTTP_400_BAD_REQUEST,
            {"code": "TASK_NOT_AWAITING_DECISION"},
        )

    if not data.accepted_solution_ids:
        raise HTTPException(
            http_status.HTTP_400_BAD_REQUEST,
            {"code": "ACCEPTED_SOLUTIONS_REQUIRED"},
        )
    if len(data.accepted_solution_ids) > 1 and not task.allow_multi_accept:
        raise HTTPException(
            http_status.HTTP_400_BAD_REQUEST,
            {"code": "MULTI_ACCEPT_NOT_ALLOWED"},
        )

    # Validate all accepted solutions belong to this task and are submitted.
    sol_rows = list((await session.scalars(
        select(Solution)
        .join(Assignment, Solution.assignment_id == Assignment.id)
        .where(
            Solution.id.in_(data.accepted_solution_ids),
            Assignment.task_id == task_id,
        )
    )).all())
    if len(sol_rows) != len(data.accepted_solution_ids):
        raise HTTPException(
            http_status.HTTP_400_BAD_REQUEST,
            {"code": "INVALID_SOLUTION_IDS"},
        )
    for s in sol_rows:
        if s.status != SolutionStatus.submitted:
            raise HTTPException(
                http_status.HTTP_400_BAD_REQUEST,
                {"code": "SOLUTION_NOT_SUBMITTED"},
            )

    decision = TaskDecision(
        task_id=task_id,
        decision_maker_id=user.id,
        accepted_solution_ids=list(data.accepted_solution_ids),
        note=data.note,
        decided_at=datetime.now(UTC),
    )
    session.add(decision)

    for s in sol_rows:
        s.status = SolutionStatus.accepted

    task.global_status = GlobalStatus.decided

    await session.commit()
    await session.refresh(decision)
    return decision


async def get_decision(
    session: AsyncSession, task_id: uuid.UUID, user: User
) -> TaskDecision:
    task = await session.get(Task, task_id)
    if not task or task.deleted_at is not None:
        raise HTTPException(http_status.HTTP_404_NOT_FOUND, {"code": "TASK_NOT_FOUND"})
    await require_project_access(session, task.project_id, user)

    decision = await session.scalar(
        select(TaskDecision).where(TaskDecision.task_id == task_id)
    )
    if not decision:
        raise HTTPException(
            http_status.HTTP_404_NOT_FOUND, {"code": "DECISION_NOT_FOUND"}
        )
    return decision


async def close_task(
    session: AsyncSession, task_id: uuid.UUID, user: User
) -> Task:
    task = await _lock_task(session, task_id)
    _require_decision_maker(task, user)

    if task.global_status != GlobalStatus.decided:
        raise HTTPException(
            http_status.HTTP_400_BAD_REQUEST,
            {"code": "TASK_NOT_DECIDED"},
        )

    task.global_status = GlobalStatus.closed
    await session.commit()
    return await session.scalar(
        select(Task)
        .options(selectinload(Task.assignments))
        .where(Task.id == task_id)
    )
