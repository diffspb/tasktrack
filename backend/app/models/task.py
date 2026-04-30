import enum
import uuid
from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, Enum as SQLEnum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin


class TaskType(str, enum.Enum):
    task = "task"
    bug = "bug"
    story = "story"


class TaskPriority(str, enum.Enum):
    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"


class GlobalStatus(str, enum.Enum):
    open = "open"
    in_progress = "in_progress"
    awaiting_decision = "awaiting_decision"
    in_revision = "in_revision"
    decided = "decided"
    closed = "closed"


class AssigneeRole(str, enum.Enum):
    lead = "lead"
    reviewer = "reviewer"
    consultant = "consultant"


class TaskLinkType(str, enum.Enum):
    blocks = "blocks"
    relates_to = "relates_to"
    duplicates = "duplicates"


class Task(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "tasks"

    project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    workflow_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workflows.id"), nullable=False
    )
    reporter_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    decision_maker_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    key: Mapped[str] = mapped_column(String(30), unique=True, nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    task_type: Mapped[TaskType] = mapped_column(
        SQLEnum(TaskType, native_enum=False, length=20),
        default=TaskType.task, nullable=False,
    )
    priority: Mapped[TaskPriority] = mapped_column(
        SQLEnum(TaskPriority, native_enum=False, length=20),
        default=TaskPriority.medium, nullable=False,
    )
    global_status: Mapped[GlobalStatus] = mapped_column(
        SQLEnum(GlobalStatus, native_enum=False, length=30),
        default=GlobalStatus.open, nullable=False,
    )
    due_date: Mapped[date | None] = mapped_column(Date)
    allow_multi_accept: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    assignments: Mapped[list["Assignment"]] = relationship(
        "Assignment", back_populates="task", cascade="all, delete-orphan"
    )


class Assignment(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "assignments"

    task_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    role: Mapped[AssigneeRole] = mapped_column(
        SQLEnum(AssigneeRole, native_enum=False, length=20), nullable=False
    )
    current_status_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("statuses.id"), nullable=False
    )
    resolution_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("resolutions.id"))

    task: Mapped["Task"] = relationship("Task", back_populates="assignments")
    solution: Mapped["Solution | None"] = relationship(  # noqa: F821
        "Solution", uselist=False, cascade="all, delete-orphan"
    )


class TaskLink(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "task_links"

    source_task_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False
    )
    target_task_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False
    )
    link_type: Mapped[TaskLinkType] = mapped_column(
        SQLEnum(TaskLinkType, native_enum=False, length=20), nullable=False
    )
    created_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
