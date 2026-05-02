import enum
import uuid

from sqlalchemy import Boolean, Enum as SQLEnum, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDMixin


class NotificationEventType(str, enum.Enum):
    task_assigned = "task_assigned"
    awaiting_decision = "awaiting_decision"
    revision_requested = "revision_requested"
    decision_made = "decision_made"
    task_closed = "task_closed"
    decision_reminder = "decision_reminder"


class NotificationEntityType(str, enum.Enum):
    task = "task"
    solution = "solution"


class Notification(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "notifications"

    recipient_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    event_type: Mapped[NotificationEventType] = mapped_column(
        SQLEnum(NotificationEventType, native_enum=False, length=40),
        nullable=False,
    )
    entity_type: Mapped[NotificationEntityType] = mapped_column(
        SQLEnum(NotificationEntityType, native_enum=False, length=20),
        nullable=False,
    )
    entity_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    task_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("tasks.id", ondelete="CASCADE")
    )
    message: Mapped[str] = mapped_column(Text, nullable=False)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    __table_args__ = (
        Index(
            "ix_notifications_recipient_unread",
            "recipient_id", "is_read", "created_at",
        ),
    )
