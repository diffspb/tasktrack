import uuid

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.project import Project, ProjectMember
from app.models.task import Task, TaskPriority
from app.models.task_type import TaskType
from app.models.user import User
from app.models.workflow import Status, Workflow
from app.schemas.task import TaskCreate, TaskStatusTransition, TaskUpdate
from app.core.events import event_bus, make_task_event
from app.services import notification_service
from app.services.permissions import require_project_access
from app.services.workflow_service import get_workflow_for_task_type, validate_transition


async def create_task(
    session: AsyncSession, project_id: uuid.UUID, data: TaskCreate, user: User
) -> Task:
    await require_project_access(session, project_id, user)

    project = await session.get(Project, project_id)

    task_type = await _resolve_task_type(session, data.task_type_key, project_id)

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

    count = await session.scalar(
        select(func.count()).select_from(Task).where(Task.project_id == project_id)
    ) or 0
    key = f"{project.key}-{count + 1}"

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

    if data.assignee_id and data.assignee_id != user.id:
        await notification_service.notify_task_assigned(session, task)

    await session.commit()
    loaded = await _load_task(session, task.id)
    event_bus.publish(str(project_id), make_task_event("task.created", loaded, str(project_id)))
    return loaded


async def get_task(
    session: AsyncSession, task_id: uuid.UUID, user: User
) -> Task:
    task = await _load_task(session, task_id)
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
) -> list[Task]:
    """Return tasks from all projects accessible to the user (for cross-project timeline)."""
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
        .where(
            Task.project_id.in_(ids),
            Task.deleted_at.is_(None),
            Task.parent_task_id.is_(None),
        )
        .order_by(Task.project_id, Task.start_date.nulls_last(), Task.created_at)
    )
    return list((await session.scalars(stmt)).all())


async def update_task(
    session: AsyncSession, task_id: uuid.UUID, data: TaskUpdate, user: User
) -> Task:
    task = await get_task(session, task_id, user)

    if data.version != task.version:
        raise HTTPException(status.HTTP_409_CONFLICT, {"code": "VERSION_CONFLICT"})

    old_assignee = task.assignee_id

    fs = data.model_fields_set
    if 'title'        in fs and data.title is not None: task.title = data.title
    if 'description'  in fs: task.description  = data.description
    if 'priority'     in fs and data.priority is not None: task.priority = data.priority
    if 'assignee_id'  in fs: task.assignee_id  = data.assignee_id
    if 'start_date'   in fs: task.start_date   = data.start_date
    if 'due_date'     in fs: task.due_date      = data.due_date
    if 'duration_days' in fs: task.duration_days = data.duration_days
    if 'meta'         in fs and data.meta is not None: task.meta = {**task.meta, **data.meta}
    task.version += 1

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
    task = await get_task(session, task_id, user)
    project_id = str(task.project_id)
    task_id_str = str(task.id)
    task.deleted_at = datetime.now(UTC)
    await session.commit()
    event_bus.publish(project_id, {"type": "task.deleted", "project_id": project_id, "task_id": task_id_str})


async def transition_status(
    session: AsyncSession,
    task_id: uuid.UUID,
    data: TaskStatusTransition,
    user: User,
) -> Task:
    task = await get_task(session, task_id, user)

    if task.assignee_id != user.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, {"code": "PERMISSION_DENIED"})

    if not await validate_transition(
        session, task.workflow_id, task.current_status_id, data.status_id
    ):
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, {"code": "WORKFLOW_TRANSITION_NOT_ALLOWED"}
        )

    # Decision-type task: blocked until all subtasks have solution_comment_id in meta.
    if task.task_type and task.task_type.key == "decision":
        await _check_decision_task_unblocked(session, task)

    task.current_status_id = data.status_id

    await session.commit()
    loaded = await _load_task(session, task.id)
    event_bus.publish(str(loaded.project_id), make_task_event("task.status_changed", loaded, str(loaded.project_id)))
    return loaded


# --- Internal helpers ---

async def _load_task(session: AsyncSession, task_id: uuid.UUID) -> Task | None:
    return await session.scalar(
        select(Task)
        .options(selectinload(Task.task_type), selectinload(Task.subtasks))
        .where(Task.id == task_id)
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


async def _check_decision_task_unblocked(
    session: AsyncSession, task: Task
) -> None:
    subtasks = list((await session.scalars(
        select(Task).where(Task.parent_task_id == task.id, Task.deleted_at.is_(None))
    )).all())
    if not subtasks:
        return
    all_ready = all(
        bool(st.meta.get("solution_comment_id")) for st in subtasks
    )
    if not all_ready:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, {"code": "TASK_BLOCKED_BY_SUBTASKS"}
        )


def get_decision_maker_id(task: Task) -> uuid.UUID | None:
    """Abstraction layer: currently DM = assignee of the decision task."""
    return task.assignee_id
