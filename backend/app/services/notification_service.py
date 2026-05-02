"""
Notification service — generic emitter + per-event helpers.

Notifications are written in the same session as the triggering business
mutation: caller is responsible for `await session.commit()` after.
"""
import uuid

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notification import (
    Notification,
    NotificationEntityType,
    NotificationEventType,
)
from app.models.task import Task


async def notify(
    session: AsyncSession,
    *,
    recipient_id: uuid.UUID,
    event_type: NotificationEventType,
    entity_type: NotificationEntityType,
    entity_id: uuid.UUID,
    message: str,
    task_id: uuid.UUID | None = None,
) -> Notification:
    n = Notification(
        recipient_id=recipient_id,
        event_type=event_type,
        entity_type=entity_type,
        entity_id=entity_id,
        task_id=task_id,
        message=message,
    )
    session.add(n)
    return n


# --- High-level emitters used from business services ---------------------

async def notify_task_assigned(session: AsyncSession, task: Task) -> None:
    if task.assignee_id is None:
        return
    await notify(
        session,
        recipient_id=task.assignee_id,
        event_type=NotificationEventType.task_assigned,
        entity_type=NotificationEntityType.task,
        entity_id=task.id,
        task_id=task.id,
        message=f"Вас назначили на задачу {task.key}: {task.title}",
    )


async def notify_awaiting_decision(session: AsyncSession, task: Task) -> None:
    dm_id = task.assignee_id
    if dm_id is None:
        return
    await notify(
        session,
        recipient_id=dm_id,
        event_type=NotificationEventType.awaiting_decision,
        entity_type=NotificationEntityType.task,
        entity_id=task.id,
        task_id=task.id,
        message=f"Все решения поданы по {task.key}: {task.title} — требуется Decision",
    )


async def notify_task_closed(session: AsyncSession, task: Task) -> None:
    if task.assignee_id is None:
        return
    await notify(
        session,
        recipient_id=task.assignee_id,
        event_type=NotificationEventType.task_closed,
        entity_type=NotificationEntityType.task,
        entity_id=task.id,
        task_id=task.id,
        message=f"Задача {task.key} закрыта: {task.title}",
    )


# --- Read-side ------------------------------------------------------------

async def list_for_user(
    session: AsyncSession,
    user_id: uuid.UUID,
    *, only_unread: bool = False, limit: int = 50, offset: int = 0,
) -> tuple[list[Notification], int, int]:
    """Returns (items, total, unread_count)."""
    base = select(Notification).where(Notification.recipient_id == user_id)
    if only_unread:
        base = base.where(Notification.is_read.is_(False))

    total = await session.scalar(
        select(func.count()).select_from(base.subquery())
    ) or 0

    unread_count = await session.scalar(
        select(func.count()).select_from(
            select(Notification).where(
                Notification.recipient_id == user_id,
                Notification.is_read.is_(False),
            ).subquery()
        )
    ) or 0

    rows = (await session.scalars(
        base.order_by(Notification.created_at.desc()).limit(limit).offset(offset)
    )).all()

    return list(rows), int(total), int(unread_count)


async def mark_read(
    session: AsyncSession, user_id: uuid.UUID, notification_id: uuid.UUID,
) -> None:
    await session.execute(
        update(Notification)
        .where(
            Notification.id == notification_id,
            Notification.recipient_id == user_id,
        )
        .values(is_read=True)
    )
    await session.commit()


async def mark_all_read(session: AsyncSession, user_id: uuid.UUID) -> None:
    await session.execute(
        update(Notification)
        .where(
            Notification.recipient_id == user_id,
            Notification.is_read.is_(False),
        )
        .values(is_read=True)
    )
    await session.commit()
