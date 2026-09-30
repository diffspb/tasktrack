"""External systems registry: providers, objects, revisions, events, snapshots (ADR-024).

Identity of an external object = provider + namespace + type + ext_id. A revision is an
opaque string; a pinned revision stores the exact bytes of the original and their SHA-256.
"""
import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean, DateTime, ForeignKey, Integer, LargeBinary, String, Text, UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin

CONTRACT_VERSION = "tasktrack-external-v1"


class ExternalProvider(Base, UUIDMixin, TimestampMixin):
    """A registered source. Authority comes from registration, never from a URL."""

    __tablename__ = "external_providers"

    key: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    kind: Mapped[str] = mapped_column(String(30), nullable=False)          # office, requirements, repository, owner, other
    acquisition: Mapped[str] = mapped_column(String(20), nullable=False)   # manual, snapshot, adapter
    # Namespaces the provider may speak for; object types it is authoritative for.
    namespaces: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    fact_types: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    # Training (test) provider: its facts never confirm readiness of real work.
    is_training: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)


class ExternalObject(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "external_objects"
    __table_args__ = (UniqueConstraint("provider_id", "namespace", "type", "ext_id"),)

    provider_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("external_providers.id"), nullable=False)
    namespace: Mapped[str] = mapped_column(String(200), nullable=False)
    type: Mapped[str] = mapped_column(String(40), nullable=False)
    ext_id: Mapped[str] = mapped_column(String(500), nullable=False)
    locator: Mapped[str | None] = mapped_column(String(2000))
    # Current revision changes only by explicit supersession, provider confirmation or a
    # full snapshot; unknown order leaves it and marks pending_reconciliation.
    current_revision: Mapped[str | None] = mapped_column(String(500))
    revision_state: Mapped[str] = mapped_column(String(30), nullable=False, default="unknown")
    state_as_of: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # active | revoked — revocation is an explicit fact with history.
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")

    provider: Mapped["ExternalProvider"] = relationship("ExternalProvider", lazy="joined")
    revisions: Mapped[list["ExternalRevision"]] = relationship(
        "ExternalRevision", back_populates="object", order_by="ExternalRevision.created_at", lazy="raise",
    )


class ExternalRevision(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "external_revisions"
    __table_args__ = (UniqueConstraint("object_id", "revision"),)

    object_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("external_objects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    revision: Mapped[str] = mapped_column(String(500), nullable=False)
    # Exact bytes of the pinned original; NULL for a reference known only from a snapshot.
    content: Mapped[bytes | None] = mapped_column(LargeBinary)
    sha256: Mapped[str | None] = mapped_column(String(64))
    media_type: Mapped[str | None] = mapped_column(String(100))
    # Parsed statements of a structured fact (JSON content).
    claims: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    asserted_by: Mapped[str | None] = mapped_column(String(500))
    registered_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    provenance: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    supersedes: Mapped[str | None] = mapped_column(String(500))
    superseded_by: Mapped[str | None] = mapped_column(String(500))
    is_revocation: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    # False: the provider is not authoritative for this type — kept as an unverified message
    # that never satisfies readiness.
    verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    object: Mapped["ExternalObject"] = relationship("ExternalObject", back_populates="revisions")


class ExternalIdentityAlias(Base, UUIDMixin, TimestampMixin):
    """Explicit mapping of a former identity to an object (identity change with history)."""

    __tablename__ = "external_identity_aliases"
    __table_args__ = (UniqueConstraint("provider_id", "namespace", "type", "ext_id"),)

    provider_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("external_providers.id"), nullable=False)
    namespace: Mapped[str] = mapped_column(String(200), nullable=False)
    type: Mapped[str] = mapped_column(String(40), nullable=False)
    ext_id: Mapped[str] = mapped_column(String(500), nullable=False)
    object_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("external_objects.id"), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    created_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)


class ExternalEvent(Base, UUIDMixin, TimestampMixin):
    """An exchange event. (provider, event_id) is unique: a repeat with the same content is
    confirmed without a second mutation, different content is a conflict."""

    __tablename__ = "external_events"
    __table_args__ = (UniqueConstraint("provider_id", "event_id"),)

    provider_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("external_providers.id"), nullable=False)
    event_id: Mapped[str] = mapped_column(String(500), nullable=False)
    contract_version: Mapped[str] = mapped_column(String(50), nullable=False)
    kind: Mapped[str] = mapped_column(String(30), nullable=False)       # revision, work_proposal
    object_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("external_objects.id"))
    revision: Mapped[str | None] = mapped_column(String(500))
    occurred_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    content_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    provenance: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    outcome: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    registered_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)


class ExternalSnapshot(Base, UUIDMixin, TimestampMixin):
    """Authoritative export for recovery. Absence of an object never deletes anything."""

    __tablename__ = "external_snapshots"

    provider_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("external_providers.id"), nullable=False)
    namespace: Mapped[str] = mapped_column(String(200), nullable=False)
    types: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    completeness: Mapped[str] = mapped_column(String(20), nullable=False)   # full, partial
    as_of: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    cursor: Mapped[str | None] = mapped_column(String(1000))               # opaque provider token
    items_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    result: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    registered_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
