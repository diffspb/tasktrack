import uuid

from sqlalchemy import ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDMixin


class WorkPackage(Base, UUIDMixin, TimestampMixin):
    """Issued, immutable version of a task's assignment (ADR-020, FR-003 TT-09).

    The editable draft lives in Task.work_package_draft; issuing validates it
    and stores a normalized copy here with a content digest.
    """

    __tablename__ = "work_packages"
    __table_args__ = (UniqueConstraint("task_id", "version"),)

    task_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False, index=True
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[dict] = mapped_column(JSONB, nullable=False)
    # sha256 of canonical JSON of `content` — identifies the exact text a worker received.
    digest: Mapped[str] = mapped_column(String(64), nullable=False)
    issued_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
