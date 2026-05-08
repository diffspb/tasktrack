from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.link_type import LinkType
from app.models.task import TaskLink
from app.models.user import User
from app.schemas.link_type import LinkTypeCreate, LinkTypeUpdate


def _require_superuser(user: User) -> None:
    if not user.is_superuser:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail={"code": "PERMISSION_DENIED"})


async def list_link_types(session: AsyncSession, include_inactive: bool = False) -> list[LinkType]:
    q = select(LinkType).order_by(LinkType.position, LinkType.name)
    if not include_inactive:
        q = q.where(LinkType.is_active.is_(True))
    return list(await session.scalars(q))


async def get_link_type(session: AsyncSession, link_type_id: UUID) -> LinkType:
    lt = await session.get(LinkType, link_type_id)
    if not lt:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail={"code": "LINK_TYPE_NOT_FOUND"})
    return lt


async def create_link_type(session: AsyncSession, data: LinkTypeCreate, user: User) -> LinkType:
    _require_superuser(user)
    existing = await session.scalar(select(LinkType).where(LinkType.name == data.name))
    if existing:
        raise HTTPException(status.HTTP_409_CONFLICT, detail={"code": "DUPLICATE_LINK_TYPE_NAME"})
    lt = LinkType(**data.model_dump())
    session.add(lt)
    await session.flush()
    await session.refresh(lt)
    return lt


async def update_link_type(session: AsyncSession, link_type_id: UUID, data: LinkTypeUpdate, user: User) -> LinkType:
    _require_superuser(user)
    lt = await get_link_type(session, link_type_id)
    for field, value in data.model_dump(exclude_none=True).items():
        setattr(lt, field, value)
    await session.flush()
    await session.refresh(lt)
    return lt


async def delete_link_type(session: AsyncSession, link_type_id: UUID, user: User) -> None:
    _require_superuser(user)
    lt = await get_link_type(session, link_type_id)
    count = await session.scalar(
        select(func.count()).where(TaskLink.link_type_id == link_type_id)
    )
    if count:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            detail={"code": "LINK_TYPE_IN_USE", "count": count},
        )
    await session.delete(lt)
    await session.flush()
