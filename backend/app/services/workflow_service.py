import uuid

from fastapi import HTTPException, status
from sqlalchemy import delete, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.workflow import (
    BoardColumn, BoardColumnStatus, ProjectTaskTypeConfig,
    Status, StatusCategory, Transition, Workflow,
)
from app.models.user import User
from app.schemas.workflow import (
    BoardColumnCreate,
    BoardColumnUpdate,
    MigrateStatus,
    SetTaskTypeWorkflow,
    StatusCreate,
    StatusUpdate,
    TransitionCreate,
    WorkflowCreate,
    WorkflowUpdate,
)
from app.services.permissions import require_manager, require_project_access


# --- Workflow ---

async def create_workflow(
    session: AsyncSession, project_id: uuid.UUID, data: WorkflowCreate, user: User
) -> Workflow:
    await require_manager(session, project_id, user)  # also validates project exists
    wf = Workflow(project_id=project_id, name=data.name, is_default=data.is_default)
    session.add(wf)
    await session.commit()
    return await _load_workflow(session, wf.id)


async def list_workflows(
    session: AsyncSession, project_id: uuid.UUID, user: User
) -> list[Workflow]:
    await require_project_access(session, project_id, user)
    result = await session.scalars(
        select(Workflow)
        .options(selectinload(Workflow.statuses), selectinload(Workflow.transitions))
        .where(Workflow.project_id == project_id)
    )
    return list(result.all())


async def get_workflow(
    session: AsyncSession, workflow_id: uuid.UUID, user: User
) -> Workflow:
    wf = await _load_workflow(session, workflow_id)
    if not wf:
        raise HTTPException(status.HTTP_404_NOT_FOUND, {"code": "WORKFLOW_NOT_FOUND"})
    # System workflows (project_id=None) are readable by any authenticated user
    if wf.project_id is not None:
        await require_project_access(session, wf.project_id, user)
    return wf


async def update_workflow(
    session: AsyncSession, workflow_id: uuid.UUID, data: WorkflowUpdate, user: User
) -> Workflow:
    wf = await _get_workflow_or_404(session, workflow_id)
    await require_manager(session, wf.project_id, user)
    if data.name is not None:
        wf.name = data.name
    if data.is_default is not None:
        wf.is_default = data.is_default
    await session.commit()
    return await _load_workflow(session, wf.id)


async def delete_workflow(
    session: AsyncSession, workflow_id: uuid.UUID, user: User
) -> None:
    wf = await _get_workflow_or_404(session, workflow_id)
    await require_manager(session, wf.project_id, user)

    if wf.is_default:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            {"code": "WORKFLOW_IS_DEFAULT", "detail": "Cannot delete the default workflow"},
        )

    from app.models.task import Task
    task_count = await session.scalar(
        select(func.count()).select_from(Task).where(Task.workflow_id == workflow_id)
    )
    if task_count:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            {"code": "WORKFLOW_HAS_TASKS"},
        )

    await session.delete(wf)
    await session.commit()


# --- Status ---

async def create_status(
    session: AsyncSession, workflow_id: uuid.UUID, data: StatusCreate, user: User
) -> Status:
    wf = await _get_workflow_or_404(session, workflow_id)
    await require_manager(session, wf.project_id, user)

    if data.is_default:
        if data.category != StatusCategory.initial:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                {"code": "STATUS_DEFAULT_MUST_BE_INITIAL"},
            )
        await _unset_default_status(session, workflow_id)

    s = Status(
        workflow_id=workflow_id,
        name=data.name,
        category=data.category,
        is_default=data.is_default,
        position=data.position,
        color=data.color,
    )
    session.add(s)
    await session.commit()
    await session.refresh(s)
    return s


async def update_status(
    session: AsyncSession, status_id: uuid.UUID, data: StatusUpdate, user: User
) -> Status:
    s = await _get_status_or_404(session, status_id)
    wf = await _get_workflow_or_404(session, s.workflow_id)
    await require_manager(session, wf.project_id, user)

    if data.color is not None:
        s.color = data.color
    if data.is_default is not None:
        if data.is_default and s.category != StatusCategory.initial:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                {"code": "STATUS_DEFAULT_MUST_BE_INITIAL"},
            )
        if data.is_default:
            await _unset_default_status(session, s.workflow_id)
        s.is_default = data.is_default
    if data.name is not None:
        s.name = data.name
    if data.position is not None:
        s.position = data.position

    await session.commit()
    await session.refresh(s)
    return s


async def delete_status(
    session: AsyncSession, status_id: uuid.UUID, user: User
) -> None:
    s = await _get_status_or_404(session, status_id)
    wf = await _get_workflow_or_404(session, s.workflow_id)
    await require_manager(session, wf.project_id, user)

    if await _count_tasks_in_status(session, status_id) > 0:
        raise HTTPException(status.HTTP_409_CONFLICT, {"code": "STATUS_HAS_ACTIVE_TASKS"})

    await _delete_status_with_transitions(session, s)


async def migrate_status(
    session: AsyncSession, status_id: uuid.UUID, data: MigrateStatus, user: User
) -> None:
    s = await _get_status_or_404(session, status_id)
    wf = await _get_workflow_or_404(session, s.workflow_id)
    await require_manager(session, wf.project_id, user)

    target = await _get_status_or_404(session, data.target_status_id)
    if target.workflow_id != s.workflow_id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, {"code": "STATUS_WORKFLOW_MISMATCH"})

    from app.models.task import Task
    await session.execute(
        update(Task)
        .where(Task.current_status_id == status_id, Task.deleted_at.is_(None))
        .values(current_status_id=data.target_status_id)
    )

    await _delete_status_with_transitions(session, s)


# --- Transition ---

async def create_transition(
    session: AsyncSession, workflow_id: uuid.UUID, data: TransitionCreate, user: User
) -> Transition:
    wf = await _get_workflow_or_404(session, workflow_id)
    await require_manager(session, wf.project_id, user)

    for sid in (data.from_status_id, data.to_status_id):
        s = await session.get(Status, sid)
        if not s or s.workflow_id != workflow_id:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                {"code": "STATUS_NOT_IN_WORKFLOW"},
            )

    t = Transition(
        workflow_id=workflow_id,
        from_status_id=data.from_status_id,
        to_status_id=data.to_status_id,
        required_role=data.required_role,
    )
    session.add(t)
    await session.commit()
    await session.refresh(t)
    return t


async def delete_transition(
    session: AsyncSession, transition_id: uuid.UUID, user: User
) -> None:
    t = await session.get(Transition, transition_id)
    if not t:
        raise HTTPException(status.HTTP_404_NOT_FOUND, {"code": "TRANSITION_NOT_FOUND"})
    wf = await _get_workflow_or_404(session, t.workflow_id)
    await require_manager(session, wf.project_id, user)
    await session.delete(t)
    await session.commit()


async def validate_transition(
    session: AsyncSession,
    workflow_id: uuid.UUID,
    from_status_id: uuid.UUID,
    to_status_id: uuid.UUID,
) -> bool:
    result = await session.scalar(
        select(Transition).where(
            Transition.workflow_id == workflow_id,
            Transition.from_status_id == from_status_id,
            Transition.to_status_id == to_status_id,
        )
    )
    return result is not None


# --- Workflow for task type selection ---

async def get_workflow_for_task_type(
    session: AsyncSession, project_id: uuid.UUID, task_type_id: uuid.UUID
) -> Workflow:
    """Fallback chain: ProjectTaskTypeConfig → TaskType.default_workflow_id → project is_default."""
    from app.models.task_type import TaskType

    config = await session.scalar(
        select(ProjectTaskTypeConfig).where(
            ProjectTaskTypeConfig.project_id == project_id,
            ProjectTaskTypeConfig.task_type_id == task_type_id,
        )
    )
    if config:
        return await _get_workflow_or_404(session, config.workflow_id)

    task_type = await session.get(TaskType, task_type_id)
    if task_type and task_type.default_workflow_id:
        return await _get_workflow_or_404(session, task_type.default_workflow_id)

    wf = await session.scalar(
        select(Workflow).where(
            Workflow.project_id == project_id, Workflow.is_default.is_(True)
        )
    )
    if wf:
        return wf

    raise HTTPException(status.HTTP_400_BAD_REQUEST, {"code": "NO_DEFAULT_WORKFLOW"})


# --- Task type configs ---

async def get_task_type_configs(
    session: AsyncSession, project_id: uuid.UUID
) -> list[dict]:
    from app.models.task_type import TaskType

    task_types = list((await session.scalars(
        select(TaskType)
        .where(or_(TaskType.is_system.is_(True), TaskType.project_id == project_id))
        .order_by(TaskType.is_system.desc(), TaskType.name)
    )).all())

    configs = list((await session.scalars(
        select(ProjectTaskTypeConfig)
        .where(ProjectTaskTypeConfig.project_id == project_id)
    )).all())
    config_map = {c.task_type_id: c for c in configs}

    project_wf = await session.scalar(
        select(Workflow).where(
            Workflow.project_id == project_id, Workflow.is_default.is_(True)
        )
    )

    result = []
    for tt in task_types:
        config = config_map.get(tt.id)
        if config:
            wf = await session.get(Workflow, config.workflow_id)
            result.append({
                "task_type_id": tt.id,
                "task_type_key": tt.key,
                "task_type_name": tt.name,
                "workflow_id": config.workflow_id,
                "workflow_name": wf.name if wf else None,
                "is_project_override": True,
            })
        elif tt.default_workflow_id:
            wf = await session.get(Workflow, tt.default_workflow_id)
            result.append({
                "task_type_id": tt.id,
                "task_type_key": tt.key,
                "task_type_name": tt.name,
                "workflow_id": tt.default_workflow_id,
                "workflow_name": wf.name if wf else None,
                "is_project_override": False,
            })
        else:
            result.append({
                "task_type_id": tt.id,
                "task_type_key": tt.key,
                "task_type_name": tt.name,
                "workflow_id": project_wf.id if project_wf else None,
                "workflow_name": project_wf.name if project_wf else None,
                "is_project_override": False,
            })

    return result


async def set_task_type_workflow(
    session: AsyncSession, project_id: uuid.UUID, task_type_id: uuid.UUID,
    data: SetTaskTypeWorkflow, user: User,
) -> ProjectTaskTypeConfig:
    await require_manager(session, project_id, user)

    wf = await session.get(Workflow, data.workflow_id)
    if not wf or (wf.project_id is not None and wf.project_id != project_id):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, {"code": "WORKFLOW_NOT_ACCESSIBLE"})

    existing = await session.scalar(
        select(ProjectTaskTypeConfig).where(
            ProjectTaskTypeConfig.project_id == project_id,
            ProjectTaskTypeConfig.task_type_id == task_type_id,
        )
    )
    if existing:
        existing.workflow_id = data.workflow_id
        await session.commit()
        await session.refresh(existing)
        return existing

    config = ProjectTaskTypeConfig(
        project_id=project_id,
        task_type_id=task_type_id,
        workflow_id=data.workflow_id,
    )
    session.add(config)
    await session.commit()
    await session.refresh(config)
    return config


async def reset_task_type_workflow(
    session: AsyncSession, project_id: uuid.UUID, task_type_id: uuid.UUID, user: User,
) -> None:
    await require_manager(session, project_id, user)
    config = await session.scalar(
        select(ProjectTaskTypeConfig).where(
            ProjectTaskTypeConfig.project_id == project_id,
            ProjectTaskTypeConfig.task_type_id == task_type_id,
        )
    )
    if config:
        await session.delete(config)
        await session.commit()


# --- Board columns ---

async def get_board_columns(
    session: AsyncSession, project_id: uuid.UUID
) -> list[BoardColumn]:
    result = await session.scalars(
        select(BoardColumn)
        .options(selectinload(BoardColumn.statuses))
        .where(BoardColumn.project_id == project_id)
        .order_by(BoardColumn.position)
    )
    return list(result.all())


async def create_board_column(
    session: AsyncSession, project_id: uuid.UUID, data: BoardColumnCreate, user: User,
) -> BoardColumn:
    await require_manager(session, project_id, user)
    col = BoardColumn(project_id=project_id, name=data.name, position=data.position)
    session.add(col)
    await session.commit()
    return await _load_board_column(session, col.id)


async def update_board_column(
    session: AsyncSession, column_id: uuid.UUID, data: BoardColumnUpdate, user: User,
) -> BoardColumn:
    col = await _get_board_column_or_404(session, column_id)
    await require_manager(session, col.project_id, user)
    if data.name is not None:
        col.name = data.name
    if data.position is not None:
        col.position = data.position
    await session.commit()
    return await _load_board_column(session, col.id)


async def delete_board_column(
    session: AsyncSession, column_id: uuid.UUID, user: User,
) -> None:
    col = await _get_board_column_or_404(session, column_id)
    await require_manager(session, col.project_id, user)
    await session.delete(col)
    await session.commit()


async def add_status_to_column(
    session: AsyncSession, column_id: uuid.UUID, status_id: uuid.UUID, user: User,
) -> BoardColumn:
    col = await _get_board_column_or_404(session, column_id)
    await require_manager(session, col.project_id, user)

    existing = await session.scalar(
        select(BoardColumnStatus).where(BoardColumnStatus.status_id == status_id)
    )
    if existing:
        raise HTTPException(status.HTTP_409_CONFLICT, {"code": "STATUS_ALREADY_MAPPED"})

    session.add(BoardColumnStatus(board_column_id=column_id, status_id=status_id))
    await session.commit()
    return await _load_board_column(session, column_id)


async def remove_status_from_column(
    session: AsyncSession, column_id: uuid.UUID, status_id: uuid.UUID, user: User,
) -> None:
    col = await _get_board_column_or_404(session, column_id)
    await require_manager(session, col.project_id, user)
    mapping = await session.scalar(
        select(BoardColumnStatus).where(
            BoardColumnStatus.board_column_id == column_id,
            BoardColumnStatus.status_id == status_id,
        )
    )
    if mapping:
        await session.delete(mapping)
        await session.commit()


# --- Internal helpers ---

async def _load_workflow(session: AsyncSession, workflow_id: uuid.UUID) -> Workflow | None:
    return await session.scalar(
        select(Workflow)
        .options(selectinload(Workflow.statuses), selectinload(Workflow.transitions))
        .where(Workflow.id == workflow_id)
    )


async def _get_workflow_or_404(session: AsyncSession, workflow_id: uuid.UUID) -> Workflow:
    wf = await session.get(Workflow, workflow_id)
    if not wf:
        raise HTTPException(status.HTTP_404_NOT_FOUND, {"code": "WORKFLOW_NOT_FOUND"})
    return wf


async def _get_status_or_404(session: AsyncSession, status_id: uuid.UUID) -> Status:
    s = await session.get(Status, status_id)
    if not s:
        raise HTTPException(status.HTTP_404_NOT_FOUND, {"code": "STATUS_NOT_FOUND"})
    return s


async def _delete_status_with_transitions(session: AsyncSession, s: Status) -> None:
    await session.execute(
        delete(Transition).where(
            or_(Transition.from_status_id == s.id, Transition.to_status_id == s.id)
        )
    )
    await session.delete(s)
    await session.commit()


async def _unset_default_status(session: AsyncSession, workflow_id: uuid.UUID) -> None:
    await session.execute(
        update(Status)
        .where(Status.workflow_id == workflow_id, Status.is_default == True)  # noqa: E712
        .values(is_default=False)
    )


async def _count_tasks_in_status(session: AsyncSession, status_id: uuid.UUID) -> int:
    from app.models.task import Task
    count = await session.scalar(
        select(func.count()).select_from(Task).where(
            Task.current_status_id == status_id,
            Task.deleted_at.is_(None),
        )
    )
    return count or 0


async def _get_board_column_or_404(session: AsyncSession, column_id: uuid.UUID) -> BoardColumn:
    col = await session.get(BoardColumn, column_id)
    if not col:
        raise HTTPException(status.HTTP_404_NOT_FOUND, {"code": "BOARD_COLUMN_NOT_FOUND"})
    return col


async def _load_board_column(session: AsyncSession, column_id: uuid.UUID) -> BoardColumn:
    result = await session.scalar(
        select(BoardColumn)
        .options(selectinload(BoardColumn.statuses))
        .where(BoardColumn.id == column_id)
    )
    if not result:
        raise HTTPException(status.HTTP_404_NOT_FOUND, {"code": "BOARD_COLUMN_NOT_FOUND"})
    return result
