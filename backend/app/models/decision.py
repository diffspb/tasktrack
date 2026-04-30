import enum
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum as SQLEnum, ForeignKey, Integer, Text
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import Uuid

from app.models.base import Base, TimestampMixin, UUIDMixin


class SolutionStatus(str, enum.Enum):
    draft = "draft"
    submitted = "submitted"
    accepted = "accepted"
    revision_requested = "revision_requested"


class Solution(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "solutions"

    assignment_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("assignments.id", ondelete="CASCADE"),
        nullable=False, unique=True,
    )
    content: Mapped[str] = mapped_column(Text, nullable=False, default="")
    status: Mapped[SolutionStatus] = mapped_column(
        SQLEnum(SolutionStatus, native_enum=False, length=30),
        default=SolutionStatus.draft, nullable=False,
    )
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revision_comment: Mapped[str | None] = mapped_column(Text)


class DecisionCriteria(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "decision_criteria"

    task_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False
    )
    description: Mapped[str] = mapped_column(Text, nullable=False)
    position: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_locked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class TaskDecision(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "task_decisions"

    task_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tasks.id", ondelete="CASCADE"),
        nullable=False, unique=True,
    )
    decision_maker_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id"), nullable=False
    )
    accepted_solution_ids: Mapped[list[uuid.UUID]] = mapped_column(
        ARRAY(Uuid(as_uuid=True)), nullable=False, default=list
    )
    note: Mapped[str | None] = mapped_column(Text)
    decided_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
