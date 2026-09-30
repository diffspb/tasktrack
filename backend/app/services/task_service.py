import uuid

from fastapi import HTTPException, status
from sqlalchemy import or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.project import Project, ProjectMember, ProjectMemberRole
from app.models.task import Task, TaskPriority
from app.models.task_type import TaskType
from app.models.user import User
from app.models.workflow import Status, StatusCategory, Workflow
from app.schemas.task import TaskCreate, TaskStatusTransition, TaskUpdate
from app.core.events import event_bus, make_task_event
from app.services import audit_service, notification_service
from app.services.audit_service import TASK_FIELDS
from app.services.meta_schema import missing_fields, validate_meta
from app.services.permissions import has_role, require_project_access, require_writer
from app.services.workflow_service import get_transition, get_workflow_for_task_type


async def create_task(
    session: AsyncSession, project_id: uuid.UUID, data: TaskCreate, user: User
) -> Task:
    await require_writer(session, project_id, user)

    project = await session.get(Project, project_id)

    task_type = await _resolve_task_type(session, data.task_type_key, project_id)
    validate_meta(task_type.meta_schema, data.meta)

    workflow_id = data.workflow_id
    if workflow_id is None:
        wf = await get_workflow_for_task_type(session, project_id, task_type.id)
        workflow_id = wf.id

    default_status = await session.scalar(
        select(Status).where(
            Status.workflow_id == workflow_id, Status.is_default.is_(True)
        )
    )
    if not default_status:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, {"code": "WORKFLOW_NO_DEFAULT_STATUS"})

    # Row lock on the project serialises numbering; released at commit.
    seq = await session.scalar(
        update(Project)
        .where(Project.id == project_id)
        .values(task_seq=Project.task_seq + 1)
        .returning(Project.task_seq)
    )
    key = f"{project.key}-{seq}"

    task = Task(
        project_id=project_id,
        workflow_id=workflow_id,
        task_type_id=task_type.id,
        reporter_id=user.id,
        assignee_id=data.assignee_id,
        parent_task_id=data.parent_task_id,
        current_status_id=default_status.id,
        key=key,
        title=data.title,
        description=data.description,
        priority=data.priority,
        start_date=data.start_date,
        due_date=data.due_date,
        meta=data.meta,
    )
    session.add(task)
    await session.flush()
    await _audit(session, task, user, "created", after=audit_service.snapshot(task, TASK_FIELDS))

    # A process type runs on its own system workflow: make its statuses visible on the boards.
    workflow = await session.get(Workflow, workflow_id)
    if workflow is not None and workflow.project_id is None:
        from app.services.workflow_service import map_workflow_to_boards
        await map_workflow_to_boards(session, project_id, workflow_id)

    if data.assignee_id and data.assignee_id != user.id:
        await notification_service.notify_task_assigned(session, task)

    await session.commit()
    loaded = await _load_task(session, task.id)
    event_bus.publish(str(project_id), make_task_event("task.created", loaded, str(project_id)))
    return loaded


async def get_task(
    session: AsyncSession, task_id: uuid.UUID, user: User, *, for_update: bool = False
) -> Task:
    task = await _load_task(session, task_id, for_update=for_update)
    if not task or task.deleted_at is not None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, {"code": "TASK_NOT_FOUND"})
    await require_project_access(session, task.project_id, user)
    return task


async def get_task_by_key(
    session: AsyncSession, key: str, user: User
) -> Task:
    task = await session.scalar(
        select(Task)
        .options(selectinload(Task.task_type), selectinload(Task.subtasks))
        .where(Task.key == key, Task.deleted_at.is_(None))
    )
    if not task:
        raise HTTPException(status.HTTP_404_NOT_FOUND, {"code": "TASK_NOT_FOUND"})
    await require_project_access(session, task.project_id, user)
    return task


async def list_tasks(
    session: AsyncSession,
    project_id: uuid.UUID,
    user: User,
    *,
    status_id: uuid.UUID | None = None,
    assignee_id: uuid.UUID | None = None,
    task_type_key: str | None = None,
    parent_task_id: uuid.UUID | None = None,
    include_subtasks: bool = True,
) -> list[Task]:
    await require_project_access(session, project_id, user)
    stmt = (
        select(Task)
        .options(selectinload(Task.task_type))
        .where(Task.project_id == project_id, Task.deleted_at.is_(None))
    )
    if status_id:
        stmt = stmt.where(Task.current_status_id == status_id)
    if assignee_id:
        stmt = stmt.where(Task.assignee_id == assignee_id)
    if task_type_key:
        stmt = stmt.join(TaskType, Task.task_type_id == TaskType.id).where(
            TaskType.key == task_type_key
        )
    if not include_subtasks:
        stmt = stmt.where(Task.parent_task_id.is_(None))
    elif parent_task_id is not None:
        stmt = stmt.where(Task.parent_task_id == parent_task_id)
    return list((await session.scalars(stmt)).all())


async def list_my_tasks(
    session: AsyncSession,
    user: User,
    *,
    role: str | None = None,
    status_id: uuid.UUID | None = None,
    project_id: uuid.UUID | None = None,
) -> list[Task]:
    if role == "assignee":
        cond = Task.assignee_id == user.id
    elif role == "reporter":
        cond = Task.reporter_id == user.id
    else:
        cond = (Task.assignee_id == user.id) | (Task.reporter_id == user.id)

    stmt = (
        select(Task)
        .options(selectinload(Task.task_type))
        .where(cond, Task.deleted_at.is_(None))
    )
    if status_id:
        stmt = stmt.where(Task.current_status_id == status_id)
    if project_id:
        stmt = stmt.where(Task.project_id == project_id)
    return list((await session.scalars(stmt)).all())


async def list_tasks_global(
    session: AsyncSession,
    user: User,
    *,
    project_ids: list[uuid.UUID] | None = None,
    q: str | None = None,
    task_type_keys: list[str] | None = None,
    limit: int = 50,
) -> list[Task]:
    """Return tasks from all projects accessible to the user.

    When q is provided: full-text search by key prefix or title substring,
    no parent_task_id restriction (any task can be found).
    Without q: returns root tasks only (for timeline view).
    """
    accessible_ids_stmt = select(ProjectMember.project_id).where(
        ProjectMember.user_id == user.id
    )
    accessible_ids = list((await session.scalars(accessible_ids_stmt)).all())

    if not accessible_ids:
        return []

    if project_ids:
        ids = [pid for pid in project_ids if pid in accessible_ids]
    else:
        ids = accessible_ids

    if not ids:
        return []

    stmt = (
        select(Task)
        .options(selectinload(Task.task_type))
        .where(Task.project_id.in_(ids), Task.deleted_at.is_(None))
    )

    if q:
        stmt = stmt.where(
            or_(
                Task.key.ilike(f"{q.upper()}%"),
                Task.title.ilike(f"%{q}%"),
            )
        ).limit(limit)
    else:
        stmt = stmt.where(Task.parent_task_id.is_(None))

    if task_type_keys:
        stmt = stmt.join(Task.task_type).where(TaskType.key.in_(task_type_keys))

    stmt = stmt.order_by(Task.project_id, Task.start_date.nulls_last(), Task.created_at)
    return list((await session.scalars(stmt)).all())


async def update_task(
    session: AsyncSession, task_id: uuid.UUID, data: TaskUpdate, user: User
) -> Task:
    task = await get_task(session, task_id, user, for_update=True)
    await require_writer(session, task.project_id, user)
    _check_version(task, data.version)

    old_assignee = task.assignee_id
    before = audit_service.snapshot(task, TASK_FIELDS)

    fs = data.model_fields_set
    if 'title'        in fs and data.title is not None: task.title = data.title
    if 'description'  in fs: task.description  = data.description
    if 'priority'     in fs and data.priority is not None: task.priority = data.priority
    if 'assignee_id'  in fs: task.assignee_id  = data.assignee_id
    if 'start_date'   in fs: task.start_date   = data.start_date
    if 'due_date'     in fs: task.due_date      = data.due_date
    if 'duration_days' in fs: task.duration_days = data.duration_days
    if 'meta'         in fs and data.meta is not None:
        task.meta = {**task.meta, **data.meta}
        validate_meta(task.task_type.meta_schema if task.task_type else None, task.meta)
    if 'reviewer_id'  in fs and data.reviewer_id != task.reviewer_id:
        from app.services.result_service import validate_designated_reviewer
        await validate_designated_reviewer(session, task, data.reviewer_id, user)
        task.reviewer_id = data.reviewer_id
    task.version += 1
    await _audit(session, task, user, "updated",
                 *audit_service.diff(before, audit_service.snapshot(task, TASK_FIELDS)))

    if data.assignee_id and data.assignee_id != old_assignee and data.assignee_id != user.id:
        await notification_service.notify_task_assigned(session, task)

    await session.commit()
    loaded = await _load_task(session, task.id)
    event_bus.publish(str(loaded.project_id), make_task_event("task.updated", loaded, str(loaded.project_id)))
    return loaded


async def delete_task(
    session: AsyncSession, task_id: uuid.UUID, user: User
) -> None:
    from datetime import UTC, datetime
    task = await get_task(session, task_id, user, for_update=True)
    await require_writer(session, task.project_id, user)
    project_id = str(task.project_id)
    task_id_str = str(task.id)
    task.deleted_at = datetime.now(UTC)
    await _audit(session, task, user, "deleted", before=audit_service.snapshot(task, TASK_FIELDS))
    await session.commit()
    event_bus.publish(project_id, {"type": "task.deleted", "project_id": project_id, "task_id": task_id_str})


async def transition_status(
    session: AsyncSession,
    task_id: uuid.UUID,
    data: TaskStatusTransition,
    user: User,
) -> Task:
    task = await get_task(session, task_id, user, for_update=True)
    member = await require_writer(session, task.project_id, user)
    if data.version is not None:
        _check_version(task, data.version)

    # Assignee moves their own task; manager/admin may move anyone's.
    if task.assignee_id != user.id and not has_role(member, ProjectMemberRole.manager):
        raise HTTPException(status.HTTP_403_FORBIDDEN, {"code": "PERMISSION_DENIED"})

    transition = await get_transition(
        session, task.workflow_id, task.current_status_id, data.status_id
    )
    if transition is None:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, {"code": "WORKFLOW_TRANSITION_NOT_ALLOWED"}
        )
    _check_transition_role(transition.required_role, member)
    missing = missing_fields(transition.required_fields or [], task.meta)
    if missing:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, {"code": "TRANSITION_FIELDS_REQUIRED", "missing": missing}
        )
    await _check_review_before_final(session, task, data.status_id)

    # Decision-type task: blocked until every subtask has presented a result.
    if task.task_type and task.task_type.key == "decision":
        await _check_decision_task_unblocked(session, task)

    before = audit_service.snapshot(task, TASK_FIELDS)
    task.current_status_id = data.status_id
    task.version += 1
    await _audit(session, task, user, "status_changed",
                 *audit_service.diff(before, audit_service.snapshot(task, TASK_FIELDS)))

    await session.commit()
    loaded = await _load_task(session, task.id)
    event_bus.publish(str(loaded.project_id), make_task_event("task.status_changed", loaded, str(loaded.project_id)))
    return loaded


# --- Internal helpers ---

async def _audit(
    session: AsyncSession, task: Task, user: User, action: str,
    before: dict | None = None, after: dict | None = None,
) -> None:
    await audit_service.record(
        session, actor_id=user.id, project_id=task.project_id, task_id=task.id,
        entity_type="task", entity_id=task.id, action=action, before=before, after=after,
    )


async def _load_task(
    session: AsyncSession, task_id: uuid.UUID, *, for_update: bool = False
) -> Task | None:
    stmt = (
        select(Task)
        .options(selectinload(Task.task_type), selectinload(Task.subtasks))
        .where(Task.id == task_id)
    )
    if for_update:
        # Lock the row until commit and re-read it: a concurrent writer that
        # committed while we waited must be visible to the version check.
        stmt = stmt.with_for_update(of=Task).execution_options(populate_existing=True)
    return await session.scalar(stmt)


def _check_version(task: Task, version: int) -> None:
    if version != task.version:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            {"code": "VERSION_CONFLICT", "current_version": task.version},
        )


async def _resolve_task_type(
    session: AsyncSession, key: str, project_id: uuid.UUID
) -> TaskType:
    task_type = await session.scalar(
        select(TaskType).where(
            TaskType.key == key,
            (TaskType.project_id == project_id) | TaskType.project_id.is_(None),
        ).order_by(TaskType.project_id.nulls_last())
    )
    if not task_type:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            {"code": "TASK_TYPE_NOT_FOUND", "key": key},
        )
    return task_type


def _check_transition_role(required_role: str | None, member: ProjectMember) -> None:
    """Transition.required_role is the minimum project role; unknown values deny (fail closed)."""
    if not required_role:
        return
    try:
        minimum = ProjectMemberRole(required_role)
    except ValueError:
        minimum = None
    if minimum is None or not has_role(member, minimum):
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            {"code": "TRANSITION_ROLE_REQUIRED", "required_role": required_role},
        )


async def _check_review_before_final(
    session: AsyncSession, task: Task, to_status_id: uuid.UUID
) -> None:
    """Task types with requires_review reach a final status only after a review verdict:
    an accepted result or a reasoned rejection (ADR-021)."""
    if not (task.task_type and task.task_type.requires_review):
        return
    target = await session.get(Status, to_status_id)
    if target is None or target.category != StatusCategory.final:
        return
    from app.services.result_service import REVIEWED_STATES
    if task.result_state not in REVIEWED_STATES:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            {"code": "RESULT_NOT_REVIEWED", "result_state": task.result_state},
        )


async def _check_decision_task_unblocked(
    session: AsyncSession, task: Task
) -> None:
    """Legacy `decision` type (ADR-016): blocked until every subtask has presented a result proposal."""
    pending = await session.scalar(
        select(Task.id).where(
            Task.parent_task_id == task.id, Task.deleted_at.is_(None), Task.result_state == "none",
        ).limit(1)
    )
    if pending is not None:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, {"code": "TASK_BLOCKED_BY_SUBTASKS"}
        )


def get_decision_maker_id(task: Task) -> uuid.UUID | None:
    """Abstraction layer: currently DM = assignee of the decision task."""
    return task.assignee_id
