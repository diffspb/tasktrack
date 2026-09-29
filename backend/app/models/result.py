import enum
import uuid

from sqlalchemy import Enum as SQLEnum, ForeignKey, Integer, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin


class ProposalStatus(str, enum.Enum):
    submitted = "submitted"                  # awaiting review
    accepted = "accepted"                    # verdict of its review
    changes_requested = "changes_requested"  # verdict of its review
    rejected = "rejected"                    # verdict of its review
    withdrawn = "withdrawn"                  # author pulled it before review
    superseded = "superseded"                # replaced by a newer version
    historical = "historical"                # migrated `solution` comment, never formally reviewed


class ReviewVerdict(str, enum.Enum):
    accepted = "accepted"
    changes_requested = "changes_requested"
    rejected = "rejected"


class ResultProposal(Base, UUIDMixin, TimestampMixin):
    """What the assignee presents as the result of a task (ADR-016, ADR-021, FR-003 TT-14).

    Content is immutable once submitted; a correction is a new version.
    """

    __tablename__ = "result_proposals"
    __table_args__ = (UniqueConstraint("task_id", "version"),)

    task_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False, index=True
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    author_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    work_package_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("work_packages.id"))
    supersedes_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("result_proposals.id"))
    status: Mapped[ProposalStatus] = mapped_column(
        SQLEnum(ProposalStatus, native_enum=False, length=30), nullable=False
    )
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    # [{kind: pr|commit|release|build|document|other, url, ref?}]
    links: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    # [{key, status: met|not_met|not_applicable, evidence?}] — keys of the work package criteria
    criteria: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    # [{name, result: passed|failed|skipped, details?}]
    checks: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    limitations: Mapped[str | None] = mapped_column(Text)
    # Where the result came from: agent/session/machine, or migration source.
    provenance: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

    reviews: Mapped[list["Review"]] = relationship(
        "Review", back_populates="proposal", order_by="Review.created_at"
    )


class Review(Base, UUIDMixin, TimestampMixin):
    """Independent check of one proposal version (ADR-021, FR-003 TT-15). Immutable."""

    __tablename__ = "reviews"

    proposal_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("result_proposals.id", ondelete="CASCADE"), nullable=False, index=True
    )
    reviewer_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    verdict: Mapped[ReviewVerdict] = mapped_column(
        SQLEnum(ReviewVerdict, native_enum=False, length=30), nullable=False
    )
    # [{key, verdict: met|not_met, note?}]
    criteria: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    rationale: Mapped[str] = mapped_column(Text, nullable=False)

    proposal: Mapped["ResultProposal"] = relationship("ResultProposal", back_populates="reviews")
