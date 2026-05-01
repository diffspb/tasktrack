import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.notification import NotificationEntityType, NotificationEventType


class NotificationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    event_type: NotificationEventType
    entity_type: NotificationEntityType
    entity_id: uuid.UUID
    task_id: uuid.UUID | None
    message: str
    is_read: bool
    created_at: datetime


class NotificationListResponse(BaseModel):
    total: int
    unread_count: int
    items: list[NotificationResponse]


class NotificationUpdate(BaseModel):
    is_read: bool
