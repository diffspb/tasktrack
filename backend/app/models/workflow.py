import enum
import uuid

from sqlalchemy import Boolean, Enum as SQLEnum, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin


class StatusCategory(str, enum.Enum):
    initial = "initial"
    intermediate = "intermediate"
    final = "final"


class Workflow(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "workflows"

    project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
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
