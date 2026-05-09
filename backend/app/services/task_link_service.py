import uuid

from fastapi import HTTPException, status
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.task import Task, TaskLink
from app.models.user import User
from app.schemas.task import TaskLinkCreate
from app.services.task_service import get_task


async def get_task_links(session: AsyncSession, task_id: uuid.UUID, user: User) -> list[TaskLink]:
    await get_task(session, task_id, user)  # access check

    stmt = (
        select(TaskLink)
        .options(
            selectinload(TaskLink.link_type),
            selectinload(TaskLink.source_task).selectinload(Task.task_type),
            selectinload(TaskLink.target_task).selectinload(Task.task_type),
        )
        .where(
            or_(
                TaskLink.source_task_id == task_id,
                TaskLink.target_task_id == task_id,
            )
        )
        .order_by(TaskLink.created_at)
    )
    return list((await session.scalars(stmt)).all())


async def create_task_link(
    session: AsyncSession, task_id: uuid.UUID, data: TaskLinkCreate, user: User
) -> TaskLink:
    await get_task(session, task_id, user)  # access check on source
    await get_task(session, data.target_task_id, user)  # access check on target

    # Prevent duplicate links in the same direction
    existing = await session.scalar(
        select(TaskLink).where(
            TaskLink.source_task_id == task_id,
            TaskLink.target_task_id == data.target_task_id,
            TaskLink.link_type_id == data.link_type_id,
        )
    )
    if existing:
        raise HTTPException(status.HTTP_409_CONFLICT, detail="Link already exists")

    link = TaskLink(
        source_task_id=task_id,
        target_task_id=data.target_task_id,
        link_type_id=data.link_type_id,
        created_by=user.id,
    )
    session.add(link)
    await session.commit()

    return await session.scalar(
        select(TaskLink)
        .options(
            selectinload(TaskLink.link_type),
            selectinload(TaskLink.source_task).selectinload(Task.task_type),
            selectinload(TaskLink.target_task).selectinload(Task.task_type),
        )
        .where(TaskLink.id == link.id)
    )


async def delete_task_link(
    session: AsyncSession, task_id: uuid.UUID, link_id: uuid.UUID, user: User
) -> None:
    await get_task(session, task_id, user)  # access check

    link = await session.scalar(
        select(TaskLink).where(
            TaskLink.id == link_id,
            or_(
                TaskLink.source_task_id == task_id,
                TaskLink.target_task_id == task_id,
            ),
        )
    )
    if not link:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Link not found")

    await session.delete(link)
    await session.commit()
