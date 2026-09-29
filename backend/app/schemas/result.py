import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.result import ProposalStatus, ReviewVerdict


class ProposalLink(BaseModel):
    kind: Literal["pr", "commit", "release", "build", "document", "other"]
    url: str = Field(min_length=1, max_length=2000)
    ref: str | None = Field(default=None, max_length=200)


class ProposalCriterion(BaseModel):
    key: str = Field(min_length=1, max_length=32)
    status: Literal["met", "not_met", "not_applicable"]
    evidence: str | None = Field(default=None, max_length=5000)


class ProposalCheck(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    result: Literal["passed", "failed", "skipped"]
    details: str | None = Field(default=None, max_length=5000)


class ProposalCreate(BaseModel):
    summary: str = Field(min_length=1, max_length=20000)
    links: list[ProposalLink] = Field(default_factory=list, max_length=50)
    criteria: list[ProposalCriterion] = Field(default_factory=list, max_length=100)
    checks: list[ProposalCheck] = Field(default_factory=list, max_length=100)
    limitations: str | None = Field(default=None, max_length=20000)
    provenance: dict = Field(default_factory=dict)
    # Defaults to the task's current work package version.
    work_package_id: uuid.UUID | None = None
    # Previous version this one replaces (after "changes requested", or before review).
    supersedes_id: uuid.UUID | None = None


class ReviewCriterion(BaseModel):
    key: str = Field(min_length=1, max_length=32)
    verdict: Literal["met", "not_met"]
    note: str | None = Field(default=None, max_length=5000)


class ReviewCreate(BaseModel):
    verdict: ReviewVerdict
    rationale: str = Field(max_length=20000)
    criteria: list[ReviewCriterion] = Field(default_factory=list, max_length=100)

    @field_validator("rationale")
    @classmethod
    def rationale_not_blank(cls, v: str) -> str:
        # A formal mark without grounds must not close the work (FR-003 TT-16).
        if not v.strip():
            raise ValueError("rationale is required")
        return v.strip()


class ReviewResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    proposal_id: uuid.UUID
    reviewer_id: uuid.UUID
    verdict: ReviewVerdict
    criteria: list
    rationale: str
    created_at: datetime


class ProposalResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    task_id: uuid.UUID
    version: int
    author_id: uuid.UUID
    work_package_id: uuid.UUID | None
    supersedes_id: uuid.UUID | None
    session_id: uuid.UUID | None = None
    status: ProposalStatus
    summary: str
    links: list
    criteria: list
    checks: list
    limitations: str | None
    provenance: dict
    created_at: datetime
    reviews: list[ReviewResponse] = []


class _QueueTask(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    key: str
    title: str
    project_id: uuid.UUID


class ReviewQueueItem(ProposalResponse):
    task: _QueueTask


class DeliveryCreate(BaseModel):
    target: str = Field(min_length=1, max_length=500)  # recipient: project, office process…
    ref: str | None = Field(default=None, max_length=500)
    note: str | None = Field(default=None, max_length=5000)


class RecipientAcceptanceCreate(BaseModel):
    """A fact received from the recipient (e.g. an office decision), not a TaskTrack verdict."""
    accepted_by: str = Field(min_length=1, max_length=500)
    accepted_at: datetime
    source: str = Field(min_length=1, max_length=100)
    ref: str | None = Field(default=None, max_length=500)
    note: str | None = Field(default=None, max_length=5000)


class MemberUpdate(BaseModel):
    role: Literal["admin", "manager", "member", "viewer"] | None = None
    is_reviewer: bool | None = None
