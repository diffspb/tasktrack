import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_session
from app.models.user import User
from app.schemas.notification import (
    NotificationListResponse,
    NotificationResponse,
    NotificationUpdate,
)
from app.services import notification_service

router = APIRouter(tags=["notifications"])


@router.get("/notifications", response_model=NotificationListResponse)
async def list_notifications(
    is_read: bool | None = None,
    limit: int = 50,
    offset: int = 0,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    items, total, unread = await notification_service.list_for_user(
        session, user.id,
        only_unread=is_read is False,
        limit=limit, offset=offset,
    )
    return NotificationListResponse(total=total, unread_count=unread, items=items)


@router.post("/notifications/read-all", status_code=status.HTTP_204_NO_CONTENT)
async def mark_all_read(
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    await notification_service.mark_all_read(session, user.id)


@router.patch("/notifications/{notification_id}", response_model=NotificationResponse)
async def mark_read(
    notification_id: uuid.UUID,
    data: NotificationUpdate,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    if data.is_read:
        await notification_service.mark_read(session, user.id, notification_id)
    n = await session.get(
        __import__("app.models.notification", fromlist=["Notification"]).Notification,
        notification_id,
    )
    return n
