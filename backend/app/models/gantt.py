import uuid

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin


class GanttChart(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "gantt_charts"

    owner_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    settings: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    position: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    task_entries: Mapped[list["GanttChartTask"]] = relationship(
        "GanttChartTask", back_populates="gantt", cascade="all, delete-orphan"
    )


class GanttChartTask(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "gantt_chart_tasks"

    gantt_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("gantt_charts.id", ondelete="CASCADE"), nullable=False
    )
    task_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False
    )
    position: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    gantt: Mapped["GanttChart"] = relationship("GanttChart", back_populates="task_entries")
