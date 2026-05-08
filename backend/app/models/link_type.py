import uuid

from sqlalchemy import Boolean, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDMixin


class LinkType(Base, UUIDMixin, TimestampMixin):
    """Global (cross-project) task link type definition."""

    __tablename__ = "link_types"

    name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    outward_name: Mapped[str] = mapped_column(String(100), nullable=False)
    inward_name: Mapped[str] = mapped_column(String(100), nullable=False)
    is_directed: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    color: Mapped[str | None] = mapped_column(String(30))
    # Optional constraint JSON, e.g.:
    #   {"type": "blocking"}
    #   {"type": "sequential", "mode": "finish_to_start"}
    constraint: Mapped[dict | None] = mapped_column(JSONB)
    position: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
