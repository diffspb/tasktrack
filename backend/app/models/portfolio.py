"""Portfolio governance on top of the external registry (ADR-024, FR-003 TT-08/10/11/19/20/21)."""
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDMixin


class ProjectPortfolioLink(Base, TimestampMixin):
    """TT-08: a project in portfolio mode — office project, main repository, regulation revision.
    No link means a standalone project: external guarantees are not applied to it."""

    __tablename__ = "project_portfolio_links"

    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), primary_key=True)
    # One local project ↔ one office project within the installation.
    office_project_object_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("external_objects.id"), unique=True, nullable=False
    )
    repository_url: Mapped[str] = mapped_column(String(1000), nullable=False)
    regulation_object_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("external_objects.id"))
    regulation_revision: Mapped[str | None] = mapped_column(String(500))
    # Project stage as a plain string (pilot, release-1…), compared for exact equality.
    stage: Mapped[str | None] = mapped_column(String(100))
    # Training project: training facts may satisfy its readiness; never a real project's.
    is_training: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    enabled_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)


class TaskBasis(Base, UUIDMixin, TimestampMixin):
    """TT-10: a typed basis of a task with a pinned revision.

    role: cause — why the work exists; input — mandatory input; normative — applicable norm;
    reference — informational; grant — allocation / authorization for the work.
    freshness: pinned — an accepted pinned snapshot is enough; confirm_current — the
    provider's current state must be confirmed (unknown blocks).
    """

    __tablename__ = "task_bases"
    __table_args__ = (UniqueConstraint("task_id", "object_id", "role"),)

    task_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False, index=True)
    object_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("external_objects.id"), nullable=False)
    revision: Mapped[str] = mapped_column(String(500), nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    meaning: Mapped[str | None] = mapped_column(String(300))
    freshness: Mapped[str] = mapped_column(String(20), nullable=False, default="pinned")
    created_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)


class TaskBlocker(Base, UUIDMixin, TimestampMixin):
    """A registered blocking reason (TT-11 condition 5)."""

    __tablename__ = "task_blockers"

    task_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False, index=True)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    source: Mapped[str] = mapped_column(String(40), nullable=False, default="manual")   # manual, impact_decision
    created_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    resolved_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    resolution: Mapped[str | None] = mapped_column(Text)


class ImpactAssessment(Base, UUIDMixin, TimestampMixin):
    """A new revision of a basis the task depends on, awaiting the manager's decision:
    continue on the old revision, reissue the package, recheck, or stop."""

    __tablename__ = "impact_assessments"

    task_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False, index=True)
    basis_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("task_bases.id", ondelete="CASCADE"), nullable=False)
    object_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("external_objects.id"), nullable=False)
    old_revision: Mapped[str] = mapped_column(String(500), nullable=False)
    new_revision: Mapped[str] = mapped_column(String(500), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")  # pending, decided
    decision: Mapped[str | None] = mapped_column(String(20))    # continue, reissue, recheck, stop
    rationale: Mapped[str | None] = mapped_column(Text)
    authority: Mapped[str | None] = mapped_column(String(500))
    decided_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class WorkProposal(Base, UUIDMixin, TimestampMixin):
    """TT-19/20: work suggested by an external source. Key: project, stage, work kind, basis
    identity (without revision), work_scope_key. A new basis revision is a new version."""

    __tablename__ = "work_proposals"
    __table_args__ = (UniqueConstraint("project_id", "stage", "work_kind", "basis_object_id", "work_scope_key"),)

    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    stage: Mapped[str] = mapped_column(String(100), nullable=False)
    work_kind: Mapped[str] = mapped_column(String(30), nullable=False)
    basis_object_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("external_objects.id"), nullable=False)
    work_scope_key: Mapped[str] = mapped_column(String(200), nullable=False)
    # open, converted (task created), linked, merged, deferred, rejected
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="open")
    task_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("tasks.id"))
    merged_into_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("work_proposals.id"))
    decision_reason: Mapped[str | None] = mapped_column(Text)
    decided_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    current_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    # A new version arrived after the manager's decision: shown, never reopens by itself.
    updated_since_decision: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


class WorkProposalVersion(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "work_proposal_versions"
    __table_args__ = (UniqueConstraint("proposal_id", "version"), UniqueConstraint("proposal_id", "basis_revision"))

    proposal_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("work_proposals.id", ondelete="CASCADE"), nullable=False, index=True
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    basis_revision: Mapped[str] = mapped_column(String(500), nullable=False)
    verification_plan_object_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("external_objects.id"))
    verification_plan_revision: Mapped[str | None] = mapped_column(String(500))
    expected_output: Mapped[str] = mapped_column(Text, nullable=False)
    result_scope: Mapped[str | None] = mapped_column(Text)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    event_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("external_events.id"))
    registered_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)


class Delivery(Base, UUIDMixin, TimestampMixin):
    """TT-17/21: a delivery of an exact accepted ResultProposal version and its WorkPackage."""

    __tablename__ = "deliveries"

    task_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False, index=True)
    proposal_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("result_proposals.id"), nullable=False)
    work_package_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("work_packages.id"))
    target: Mapped[str] = mapped_column(String(500), nullable=False)
    recipient_object_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("external_objects.id"))
    ref: Mapped[str | None] = mapped_column(String(500))
    note: Mapped[str | None] = mapped_column(Text)
    proposed_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)


class RecipientAcceptance(Base, UUIDMixin, TimestampMixin):
    """The recipient's decision on an exact delivery — a received fact with author, date and
    authority. Historical manual records without a binding keep historical=True."""

    __tablename__ = "recipient_acceptances"

    task_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False, index=True)
    delivery_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("deliveries.id"))
    proposal_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("result_proposals.id"))
    work_package_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("work_packages.id"))
    recipient: Mapped[str] = mapped_column(String(500), nullable=False)
    usage_scope: Mapped[str | None] = mapped_column(String(500))
    accepted_by: Mapped[str] = mapped_column(String(500), nullable=False)
    accepted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    authority: Mapped[str | None] = mapped_column(String(500))
    source: Mapped[str] = mapped_column(String(100), nullable=False)
    ref: Mapped[str | None] = mapped_column(String(500))
    note: Mapped[str | None] = mapped_column(Text)
    fact_revision_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("external_revisions.id"))
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="accepted")   # accepted, withdrawn
    historical: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    recorded_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    withdrawn_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    withdrawal_reason: Mapped[str | None] = mapped_column(Text)
