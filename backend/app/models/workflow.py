import enum
import uuid

from sqlalchemy import Boolean, Enum as SQLEnum, ForeignKey, Index, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin


class StatusCategory(str, enum.Enum):
    initial = "initial"
    intermediate = "intermediate"
    final = "final"


class ViewType(str, enum.Enum):
    kanban = "kanban"
    backlog = "backlog"


class View(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "views"

    project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    type: Mapped[ViewType] = mapped_column(
        SQLEnum(ViewType, native_enum=False, length=20), nullable=False
    )
    position: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    columns: Mapped[list["BoardColumn"]] = relationship(
        "BoardColumn", back_populates="view", cascade="all, delete-orphan"
    )

    __table_args__ = (Index("ix_views_project_position", "project_id", "position"),)


class Workflow(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "workflows"

    project_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    statuses: Mapped[list["Status"]] = relationship(
        "Status", back_populates="workflow", cascade="all, delete-orphan"
    )
    transitions: Mapped[list["Transition"]] = relationship(
        "Transition", back_populates="workflow", cascade="all, delete-orphan"
    )


class Status(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "statuses"

    workflow_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workflows.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[StatusCategory] = mapped_column(
        SQLEnum(StatusCategory, native_enum=False, length=20), nullable=False
    )
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    position: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    color: Mapped[str | None] = mapped_column(String(7))  # hex color, e.g. "#3B82F6"

    workflow: Mapped["Workflow"] = relationship("Workflow", back_populates="statuses")


class Transition(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "transitions"

    workflow_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workflows.id", ondelete="CASCADE"), nullable=False
    )
    from_status_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("statuses.id", ondelete="CASCADE"), nullable=False
    )
    to_status_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("statuses.id", ondelete="CASCADE"), nullable=False
    )
    required_role: Mapped[str | None] = mapped_column(String(50))

    workflow: Mapped["Workflow"] = relationship("Workflow", back_populates="transitions")
    from_status: Mapped["Status"] = relationship("Status", foreign_keys=[from_status_id])
    to_status: Mapped["Status"] = relationship("Status", foreign_keys=[to_status_id])


class ProjectTaskTypeConfig(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "project_task_type_configs"

    project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    task_type_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("task_types.id", ondelete="CASCADE"), nullable=False
    )
    workflow_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workflows.id", ondelete="CASCADE"), nullable=False
    )

    __table_args__ = (UniqueConstraint("project_id", "task_type_id"),)


class BoardColumn(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "board_columns"

    view_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("views.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    position: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    view: Mapped["View"] = relationship("View", back_populates="columns")
    statuses: Mapped[list["BoardColumnStatus"]] = relationship(
        "BoardColumnStatus", back_populates="column", cascade="all, delete-orphan"
    )

    __table_args__ = (Index("ix_board_columns_view_position", "view_id", "position"),)

    @property
    def status_ids(self) -> list[uuid.UUID]:
        return [s.status_id for s in self.statuses]


class BoardColumnStatus(Base):
    __tablename__ = "board_column_statuses"

    board_column_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("board_columns.id", ondelete="CASCADE"), primary_key=True
    )
    status_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("statuses.id", ondelete="CASCADE"), primary_key=True,
        # unique=True removed — same status can appear in columns of different views
    )

    column: Mapped["BoardColumn"] = relationship("BoardColumn", back_populates="statuses")
