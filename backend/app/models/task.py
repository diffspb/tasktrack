import enum
import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, Enum as SQLEnum, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, TSVECTOR
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin


class TaskPriority(str, enum.Enum):
    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"



class Task(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "tasks"

    project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    workflow_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workflows.id"), nullable=False
    )
    task_type_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("task_types.id"), nullable=False
    )
    reporter_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    assignee_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    parent_task_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("tasks.id"))
    current_status_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("statuses.id"), nullable=False
    )

    key: Mapped[str] = mapped_column(String(30), unique=True, nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    priority: Mapped[TaskPriority] = mapped_column(
        SQLEnum(TaskPriority, native_enum=False, length=20),
        default=TaskPriority.medium, nullable=False,
    )
    meta: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    start_date: Mapped[date | None] = mapped_column(Date)
    due_date: Mapped[date | None] = mapped_column(Date)
    duration_days: Mapped[int | None] = mapped_column(Integer)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    # Updated by a Postgres trigger; see app.core.db.create_tables.
    search_vector: Mapped[str | None] = mapped_column(TSVECTOR)

    task_type: Mapped["TaskType"] = relationship("TaskType")  # noqa: F821
    subtasks: Mapped[list["Task"]] = relationship(
        "Task", foreign_keys="[Task.parent_task_id]"
    )
    comments: Mapped[list["Comment"]] = relationship(  # noqa: F821
        "Comment", back_populates="task", cascade="all, delete-orphan"
    )


class TaskLink(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "task_links"

    source_task_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False
    )
    target_task_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False
    )
    link_type_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("link_types.id", ondelete="RESTRICT"), nullable=False
    )
    created_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)

    link_type: Mapped["LinkType"] = relationship("LinkType")  # noqa: F821
