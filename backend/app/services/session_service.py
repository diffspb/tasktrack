"""Work sessions on tasks (ADR-022, FR-003 TT-12)."""
import contextvars
import uuid
from datetime import UTC, datetime

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.project import ProjectMemberRole
from app.models.session import SessionCheckpoint, TaskSession
from app.models.task import Task
from app.models.user import User
from app.models.work_package import WorkPackage
from app.schemas.session import CheckpointCreate, SessionComplete, SessionCreate, SessionRelease
from app.services import audit_service
from app.services.permissions import has_role, require_writer
from app.services.task_service import get_task

# Session named by the request's X-Task-Session header, validated by task_session_guard.
current_session: contextvars.ContextVar[TaskSession | None] = contextvars.ContextVar(
    "current_session", default=None
)


async def claim(session: AsyncSession, task_id: uuid.UUID, data: SessionCreate, user: User) -> TaskSession:
    task = await get_task(session, task_id, user, for_update=True)  # serializes claims per task
    member = await require_writer(session, task.project_id, user)
    if data.role == "executor":
        if task.assignee_id != user.id:
            raise HTTPException(status.HTTP_403_FORBIDDEN, {"code": "NOT_ASSIGNEE"})
        active = await active_executor(session, task.id)
        if active is not None:
            raise _session_active(active)
        # Portfolio mode: a new execution starts only when the task is ready (ADR-024, TT-11).
        from app.services.portfolio_service import require_ready
        await require_ready(session, task)
    elif not member.is_reviewer or user.id == task.assignee_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, {"code": "NOT_REVIEWER"})

    package_id = None
    if task.work_package_version is not None:
        package_id = await session.scalar(select(WorkPackage.id).where(
            WorkPackage.task_id == task.id, WorkPackage.version == task.work_package_version,
        ))
    row = TaskSession(
        task_id=task.id, user_id=user.id, work_package_id=package_id, role=data.role,
        state="active", machine=data.machine, workdir=data.workdir, client=data.client,
    )
    session.add(row)
    try:
        await session.flush()
    except IntegrityError:  # backstop: the partial unique index
        await session.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, {"code": "SESSION_ACTIVE"})
    await _audit(session, task, user, row, "started", after=_snapshot(row))
    await session.commit()
    return await get_session_row(session, row.id, user)


async def add_checkpoint(
    session: AsyncSession, session_id: uuid.UUID, data: CheckpointCreate, user: User
) -> SessionCheckpoint:
    row, task = await _load_own_active(session, session_id, user)
    checkpoint = SessionCheckpoint(session_id=row.id, note=data.note, data=data.data)
    session.add(checkpoint)
    row.last_checkpoint_at = datetime.now(UTC)
    await session.flush()
    await _audit(session, task, user, row, "checkpoint", after={"note": data.note})
    await session.commit()
    await session.refresh(checkpoint)
    return checkpoint


async def complete(
    session: AsyncSession, session_id: uuid.UUID, data: SessionComplete, user: User
) -> TaskSession:
    row, task = await _load_own_active(session, session_id, user)
    row.state = "completed"
    row.result = data.result
    row.ended_at, row.ended_by = datetime.now(UTC), user.id
    await _audit(session, task, user, row, "completed", after={"result": data.result})
    await session.commit()
    return await get_session_row(session, row.id, user)


async def release(
    session: AsyncSession, session_id: uuid.UUID, data: SessionRelease, user: User
) -> TaskSession:
    """Explicit decision to end someone's (or one's own) session, e.g. after the
    process was verified stopped. Time without checkpoints never ends a session."""
    row, task = await _load_active(session, session_id, user)
    member = await require_writer(session, task.project_id, user)
    if row.user_id != user.id and not has_role(member, ProjectMemberRole.manager):
        raise HTTPException(status.HTTP_403_FORBIDDEN, {"code": "PERMISSION_DENIED"})
    row.state = "released"
    row.end_reason = data.reason
    row.ended_at, row.ended_by = datetime.now(UTC), user.id
    await _audit(session, task, user, row, "released", after={"reason": data.reason})
    await session.commit()
    return await get_session_row(session, row.id, user)


async def get_session_row(session: AsyncSession, session_id: uuid.UUID, user: User) -> TaskSession:
    row = await session.scalar(
        select(TaskSession).options(selectinload(TaskSession.checkpoints))
        .where(TaskSession.id == session_id).execution_options(populate_existing=True)
    )
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, {"code": "SESSION_NOT_FOUND"})
    await get_task(session, row.task_id, user)  # read access
    return row


async def list_for_task(session: AsyncSession, task_id: uuid.UUID, user: User) -> list[TaskSession]:
    await get_task(session, task_id, user)
    return list((await session.scalars(
        select(TaskSession).options(selectinload(TaskSession.checkpoints))
        .where(TaskSession.task_id == task_id).order_by(TaskSession.created_at)
    )).all())


async def active_executor(session: AsyncSession, task_id: uuid.UUID) -> TaskSession | None:
    return await session.scalar(select(TaskSession).where(
        TaskSession.task_id == task_id, TaskSession.state == "active", TaskSession.role == "executor",
    ))


async def resolve_header(session: AsyncSession, raw: str, user: User) -> TaskSession:
    """X-Task-Session must name the caller's own active session."""
    try:
        session_id = uuid.UUID(raw)
    except ValueError:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, {"code": "SESSION_HEADER_INVALID"})
    row = await session.get(TaskSession, session_id)
    if row is None or row.state != "active" or row.user_id != user.id:
        raise HTTPException(status.HTTP_409_CONFLICT, {"code": "SESSION_NOT_ACTIVE"})
    return row


def provenance(row: TaskSession) -> dict:
    return {"session": {
        "id": str(row.id), "machine": row.machine, "workdir": row.workdir, "client": row.client,
        "work_package_id": str(row.work_package_id) if row.work_package_id else None,
    }}


def _session_active(active: TaskSession) -> HTTPException:
    return HTTPException(status.HTTP_409_CONFLICT, {
        "code": "SESSION_ACTIVE", "session_id": str(active.id), "user_id": str(active.user_id),
        "machine": active.machine, "started_at": active.created_at.isoformat(),
        "last_checkpoint_at": active.last_checkpoint_at.isoformat() if active.last_checkpoint_at else None,
    })


async def _load_active(session: AsyncSession, session_id: uuid.UUID, user: User) -> tuple[TaskSession, Task]:
    row = await session.get(TaskSession, session_id)
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, {"code": "SESSION_NOT_FOUND"})
    task = await get_task(session, row.task_id, user, for_update=True)
    row = await session.scalar(
        select(TaskSession).where(TaskSession.id == session_id)
        .with_for_update().execution_options(populate_existing=True)
    )
    if row.state != "active":
        raise HTTPException(status.HTTP_409_CONFLICT, {"code": "SESSION_NOT_ACTIVE"})
    return row, task


async def _load_own_active(session: AsyncSession, session_id: uuid.UUID, user: User) -> tuple[TaskSession, Task]:
    row, task = await _load_active(session, session_id, user)
    if row.user_id != user.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, {"code": "PERMISSION_DENIED"})
    return row, task


def _snapshot(row: TaskSession) -> dict:
    return audit_service.snapshot(row, ("role", "machine", "workdir", "client", "work_package_id"))


async def _audit(session: AsyncSession, task: Task, user: User, row: TaskSession, action: str,
                 before: dict | None = None, after: dict | None = None) -> None:
    await audit_service.record(
        session, actor_id=user.id, project_id=task.project_id, task_id=task.id,
        entity_type="task_session", entity_id=row.id, action=action, before=before, after=after,
    )
