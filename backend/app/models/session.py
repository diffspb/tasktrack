import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin


class TaskSession(Base, UUIDMixin, TimestampMixin):
    """A concrete run of work on a task: who, where, which assignment version (ADR-022, FR-003 TT-12).

    At most one active executor session per task — enforced by a partial unique
    index, so two processes (even under one account) never both hold it.
    A session ends only explicitly: completed by its owner or released with a
    reason; losing the connection does not end it.
    """

    __tablename__ = "task_sessions"
    __table_args__ = (
        Index(
            "uq_task_sessions_active_executor", "task_id", unique=True,
            postgresql_where=text("state = 'active' AND role = 'executor'"),
        ),
    )

    task_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    work_package_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("work_packages.id"))
    role: Mapped[str] = mapped_column(String(20), nullable=False, default="executor")
    state: Mapped[str] = mapped_column(String(20), nullable=False, default="active")
    machine: Mapped[str | None] = mapped_column(String(200))
    workdir: Mapped[str | None] = mapped_column(String(1000))
    client: Mapped[str | None] = mapped_column(String(200))
    last_checkpoint_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    ended_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    end_reason: Mapped[str | None] = mapped_column(Text)
    result: Mapped[str | None] = mapped_column(Text)

    checkpoints: Mapped[list["SessionCheckpoint"]] = relationship(
        "SessionCheckpoint", order_by="SessionCheckpoint.created_at", cascade="all, delete-orphan"
    )


class SessionCheckpoint(Base, UUIDMixin, TimestampMixin):
    """Saved on a significant result and before a long or external action;
    recovery after a crash starts from the last one."""

    __tablename__ = "session_checkpoints"

    session_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("task_sessions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    note: Mapped[str] = mapped_column(Text, nullable=False)
    data: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
