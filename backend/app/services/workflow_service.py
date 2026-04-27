import uuid

from fastapi import HTTPException, status
from sqlalchemy import delete, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.workflow import Status, StatusCategory, Transition, Workflow
from app.models.user import User
from app.schemas.workflow import (
    MigrateStatus,
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
    # Phase 3+: check that no active tasks reference this workflow before deleting

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

    if await _count_active_assignments(session, status_id) > 0:
        raise HTTPException(status.HTTP_409_CONFLICT, {"code": "STATUS_HAS_ACTIVE_ASSIGNMENTS"})

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

    # Phase 3+: migrate active Assignment.current_status_id → data.target_status_id
    # from sqlalchemy import update as sa_update
    # from app.models.task import Assignment
    # await session.execute(
    #     sa_update(Assignment)
    #     .where(Assignment.current_status_id == status_id)
    #     .values(current_status_id=data.target_status_id)
    # )

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


async def _count_active_assignments(session: AsyncSession, status_id: uuid.UUID) -> int:
    """Phase 3+ will query Assignment.current_status_id here. Returns 0 until Phase 3."""
    # TODO(phase-3): from app.models.task import Assignment; query count
    return 0
