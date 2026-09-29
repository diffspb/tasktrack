import uuid
from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Integer, String, Text, func, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class IdempotencyKey(Base):
    """Remembered outcome of a command sent with an Idempotency-Key (ADR-019, FR-003 TT-04).

    The row is inserted before the command runs, in the command's own transaction:
    it exists only if the command committed. The response is stored right after.
    """

    __tablename__ = "idempotency_keys"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    key: Mapped[str] = mapped_column(String(255), primary_key=True)
    request_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    # Transaction of the command: links the key to the audit events it produced.
    xid: Mapped[int] = mapped_column(
        BigInteger, nullable=False, server_default=text("(pg_current_xact_id()::text)::bigint")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status_code: Mapped[int | None] = mapped_column(Integer)
    response_body: Mapped[str | None] = mapped_column(Text)
    media_type: Mapped[str | None] = mapped_column(String(100))
    # Projects the command changed (from its audit events) — write access is re-checked on replay.
    project_ids: Mapped[list | None] = mapped_column(JSONB)
    # The command produced system-level events (project_id IS NULL) — replay needs a superuser.
    system: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
