import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin


class Comment(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "comments"

    task_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False
    )
    author_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    parent_comment_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("comments.id"))
    content: Mapped[str] = mapped_column(Text, nullable=False)
    labels: Mapped[list[str]] = mapped_column(
        ARRAY(String(50)), default=list, nullable=False
    )
    edited_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    task: Mapped["Task"] = relationship("Task", back_populates="comments")  # noqa: F821
    replies: Mapped[list["Comment"]] = relationship(
        "Comment", foreign_keys=[parent_comment_id]
    )
