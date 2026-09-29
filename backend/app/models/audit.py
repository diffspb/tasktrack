import uuid
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Identity, Index, String, Text, Uuid, func, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class AuditEvent(Base):
    """Append-only record of a significant change, written in the same transaction
    as the change itself (ADR-018, FR-003 TT-06).

    No foreign keys on purpose: the record must outlive the rows it describes.
    Consumers read it in (xid, id) order — see audit_service.list_events.
    """

    __tablename__ = "audit_events"

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    # Top-level transaction id of the writer; part of the gap-free read cursor.
    xid: Mapped[int] = mapped_column(
        BigInteger, nullable=False, server_default=text("(pg_current_xact_id()::text)::bigint")
    )
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    actor_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True))
    # NULL for system-level events (service accounts, API keys).
    project_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True))
    # The task the change belongs to (task itself, its comment or link) — for task history.
    task_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True))
    # Work session the change was made in (X-Task-Session, ADR-022), if any.
    session_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True))
    entity_type: Mapped[str] = mapped_column(String(30), nullable=False)
    entity_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    action: Mapped[str] = mapped_column(String(30), nullable=False)
    reason: Mapped[str | None] = mapped_column(Text)
    before: Mapped[dict | None] = mapped_column(JSONB)
    after: Mapped[dict | None] = mapped_column(JSONB)

    __table_args__ = (
        Index("ix_audit_events_project_cursor", "project_id", "xid", "id"),
        Index("ix_audit_events_task_cursor", "task_id", "xid", "id"),
    )
