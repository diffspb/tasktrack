import uuid

from fastapi import HTTPException, status
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.resolution import Resolution
from app.models.user import User
from app.schemas.resolution import ResolutionCreate, ResolutionUpdate
from app.services.permissions import require_manager, require_project_access


async def list_resolutions(
    session: AsyncSession, project_id: uuid.UUID, user: User
) -> list[Resolution]:
    await require_project_access(session, project_id, user)
    result = await session.scalars(
        select(Resolution)
        .where(Resolution.project_id == project_id)
        .order_by(Resolution.position)
    )
    return list(result.all())


async def create_resolution(
    session: AsyncSession, project_id: uuid.UUID, data: ResolutionCreate, user: User
) -> Resolution:
    await require_manager(session, project_id, user)

    if data.is_default:
        await _unset_default(session, project_id)

    r = Resolution(
        project_id=project_id,
        name=data.name,
        is_default=data.is_default,
        position=data.position,
    )
    session.add(r)
    await session.commit()
    await session.refresh(r)
    return r


async def update_resolution(
    session: AsyncSession, resolution_id: uuid.UUID, data: ResolutionUpdate, user: User
) -> Resolution:
    r = await _get_or_404(session, resolution_id)
    await require_manager(session, r.project_id, user)

    if data.is_default:
        await _unset_default(session, r.project_id)
    if data.name is not None:
        r.name = data.name
    if data.is_default is not None:
        r.is_default = data.is_default
    if data.position is not None:
        r.position = data.position

    await session.commit()
    await session.refresh(r)
    return r


async def delete_resolution(
    session: AsyncSession, resolution_id: uuid.UUID, user: User
) -> None:
    r = await _get_or_404(session, resolution_id)
    await require_manager(session, r.project_id, user)
    await session.delete(r)
    await session.commit()


async def _get_or_404(session: AsyncSession, resolution_id: uuid.UUID) -> Resolution:
    r = await session.get(Resolution, resolution_id)
    if not r:
        raise HTTPException(status.HTTP_404_NOT_FOUND, {"code": "RESOLUTION_NOT_FOUND"})
    return r


async def _unset_default(session: AsyncSession, project_id: uuid.UUID) -> None:
    await session.execute(
        update(Resolution)
        .where(Resolution.project_id == project_id, Resolution.is_default == True)  # noqa: E712
        .values(is_default=False)
    )
