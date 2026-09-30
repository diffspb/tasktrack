"""External contract v1.0 (ADR-024): registry, facts, snapshots, portfolio, work proposals."""
import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.external import CONTRACT_VERSION

ObjectType = Literal[
    "project", "requirement", "verification_plan", "issue", "risk", "mitigation", "decision",
    "regulation", "initiative", "migration", "allocation", "authorization", "input_acceptance",
    "commitment", "delivery", "recipient_acceptance", "evidence", "office_process",
]
BasisRole = Literal["cause", "input", "normative", "reference", "grant"]
Freshness = Literal["pinned", "confirm_current"]
WorkKind = Literal[
    "research", "implementation", "verification", "reverification", "fix", "migration", "impact_assessment",
]
_KEY = r"^[a-z0-9][a-z0-9._-]{0,99}$"


class ObjectRef(BaseModel):
    """Identity: provider + namespace + type + id. The locator is not part of it."""

    provider: str = Field(min_length=1, max_length=100)
    namespace: str = Field(min_length=1, max_length=200)
    type: ObjectType
    id: str = Field(min_length=1, max_length=500)


class RevisionRef(ObjectRef):
    revision: str = Field(min_length=1, max_length=500)


# ── Provider registry ────────────────────────────────────────────────────────

class ProviderCreate(BaseModel):
    key: str = Field(pattern=_KEY)
    name: str = Field(min_length=1, max_length=200)
    kind: Literal["office", "requirements", "repository", "owner", "other"]
    acquisition: Literal["manual", "snapshot", "adapter"] = "manual"
    namespaces: list[str] = Field(default_factory=list, max_length=200)
    fact_types: list[ObjectType] = Field(default_factory=list)
    is_training: bool = False


class ProviderUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    acquisition: Literal["manual", "snapshot", "adapter"] | None = None
    namespaces: list[str] | None = Field(default=None, max_length=200)
    fact_types: list[ObjectType] | None = None
    active: bool | None = None


class ProviderResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    key: str
    name: str
    kind: str
    acquisition: str
    namespaces: list[str]
    fact_types: list[str]
    is_training: bool
    active: bool
    created_at: datetime


# ── Facts, events, snapshots ─────────────────────────────────────────────────

class _Content(BaseModel):
    # Structured content (pinned once as canonical JSON, parsed into claims) or exact bytes.
    content: dict | None = None
    content_base64: str | None = None
    media_type: str | None = Field(default=None, max_length=100)
    claims: dict | None = None  # parsed statements for byte content

    @model_validator(mode="after")
    def one_content(self):
        if self.content is not None and self.content_base64 is not None:
            raise ValueError("pass either content or content_base64")
        return self


class FactImport(_Content, ObjectRef):
    """Manual registration of a revision / fact. The same rules apply to a future adapter."""

    project_id: uuid.UUID | None = None   # rights scope: a manager of this project may import
    revision: str | None = Field(default=None, max_length=500)  # omitted → sha256:<hex> of the bytes
    locator: str | None = Field(default=None, max_length=2000)
    observed_at: datetime
    asserted_by: str | None = Field(default=None, max_length=500)
    provenance: dict = Field(default_factory=dict)
    supersedes: str | None = Field(default=None, max_length=500)
    confirmed_current: bool = False   # the provider confirms this is its current revision
    revoked: bool = False             # explicit revocation fact
    event_id: str | None = Field(default=None, min_length=1, max_length=500)
    contract_version: str = CONTRACT_VERSION


class ObjectResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    provider: str
    namespace: str
    type: str
    ext_id: str
    locator: str | None
    current_revision: str | None
    revision_state: str
    state_as_of: datetime | None
    status: str
    is_training: bool


class RevisionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    object_id: uuid.UUID
    revision: str
    sha256: str | None
    media_type: str | None
    claims: dict
    observed_at: datetime
    created_at: datetime
    asserted_by: str | None
    registered_by: uuid.UUID
    provenance: dict
    supersedes: str | None
    superseded_by: str | None
    is_revocation: bool
    verified: bool


class FactImportResult(BaseModel):
    object: ObjectResponse
    revision: RevisionResponse
    replayed: bool      # an event repeated with the same content — no second mutation
    outcome: dict


class ObjectDetail(BaseModel):
    object: ObjectResponse
    revisions: list[RevisionResponse]
    aliases: list[ObjectRef]


class SnapshotItem(_Content):
    type: ObjectType
    id: str = Field(min_length=1, max_length=500)
    revision: str | None = Field(default=None, max_length=500)
    locator: str | None = Field(default=None, max_length=2000)
    revoked: bool = False


class SnapshotImport(BaseModel):
    project_id: uuid.UUID | None = None
    provider: str = Field(min_length=1, max_length=100)
    namespace: str = Field(min_length=1, max_length=200)
    types: list[ObjectType] = Field(min_length=1)
    completeness: Literal["full", "partial"]
    as_of: datetime
    cursor: str | None = Field(default=None, max_length=1000)
    items: list[SnapshotItem] = Field(default_factory=list, max_length=5000)
    event_id: str | None = Field(default=None, min_length=1, max_length=500)
    contract_version: str = CONTRACT_VERSION


class SnapshotResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    namespace: str
    types: list[str]
    completeness: str
    as_of: datetime
    cursor: str | None
    items_count: int
    result: dict
    created_at: datetime
    replayed: bool = False


class AliasCreate(BaseModel):
    old: ObjectRef
    current: ObjectRef
    reason: str = Field(min_length=1, max_length=2000)


class EventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    event_id: str
    contract_version: str
    kind: str
    object_id: uuid.UUID | None
    revision: str | None
    occurred_at: datetime | None
    content_sha256: str
    provenance: dict
    outcome: dict
    created_at: datetime


# ── Project portfolio link (TT-08) ───────────────────────────────────────────

class OfficeProjectRef(BaseModel):
    provider: str = Field(min_length=1, max_length=100)
    namespace: str = Field(min_length=1, max_length=200)
    id: str = Field(min_length=1, max_length=500)


class PortfolioLinkSet(BaseModel):
    office_project: OfficeProjectRef
    repository_url: str = Field(min_length=1, max_length=1000)
    regulation: RevisionRef | None = None
    stage: str | None = Field(default=None, min_length=1, max_length=100)
    is_training: bool = False


class PortfolioLinkResponse(BaseModel):
    project_id: uuid.UUID
    office_project: ObjectResponse
    repository_url: str
    regulation: ObjectResponse | None
    regulation_revision: str | None
    stage: str | None
    is_training: bool
    recipient: str   # how facts address this project
    created_at: datetime


# ── Task bases, readiness, blockers, impact (TT-10/11) ───────────────────────

class BasisCreate(BaseModel):
    object: ObjectRef
    revision: str = Field(min_length=1, max_length=500)
    role: BasisRole
    meaning: str | None = Field(default=None, max_length=300)
    freshness: Freshness = "pinned"


class BasisResponse(BaseModel):
    id: uuid.UUID
    task_id: uuid.UUID
    object: ObjectResponse
    revision: str
    role: str
    meaning: str | None
    freshness: str
    verified: bool
    created_at: datetime
    evidence: list[RevisionResponse] = []


class BlockerCreate(BaseModel):
    reason: str = Field(min_length=1, max_length=5000)


class BlockerResolve(BaseModel):
    resolution: str = Field(min_length=1, max_length=5000)


class BlockerResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    task_id: uuid.UUID
    reason: str
    source: str
    created_by: uuid.UUID
    created_at: datetime
    resolved_at: datetime | None
    resolved_by: uuid.UUID | None
    resolution: str | None


class ImpactDecision(BaseModel):
    decision: Literal["continue", "reissue", "recheck", "stop"]
    rationale: str = Field(min_length=1, max_length=5000)
    authority: str | None = Field(default=None, max_length=500)


class ImpactResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    task_id: uuid.UUID
    basis_id: uuid.UUID
    object_id: uuid.UUID
    old_revision: str
    new_revision: str
    status: str
    decision: str | None
    rationale: str | None
    authority: str | None
    decided_by: uuid.UUID | None
    decided_at: datetime | None
    created_at: datetime


class ReadinessReason(BaseModel):
    code: str
    message: str
    basis_id: uuid.UUID | None = None
    object: dict | None = None
    revision: str | None = None
    as_of: datetime | None = None


class ReadinessCondition(BaseModel):
    key: Literal["package", "inputs", "normative", "grant", "blockers"]
    ok: bool
    reasons: list[ReadinessReason]
    facts: list[dict] = []


class Readiness(BaseModel):
    mode: Literal["standalone", "portfolio"]
    ready: bool
    checked_at: datetime
    conditions: list[ReadinessCondition]


# ── Work proposals (TT-19/20) ────────────────────────────────────────────────

class WorkProposalImport(BaseModel):
    provider: str = Field(min_length=1, max_length=100)   # the source reporting the gap
    stage: str = Field(min_length=1, max_length=100)
    work_kind: WorkKind
    basis: RevisionRef
    verification_plan: RevisionRef | None = None
    work_scope_key: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,199}$")
    result_scope: str | None = Field(default=None, max_length=5000)
    expected_output: str = Field(min_length=1, max_length=5000)
    reason: str = Field(min_length=1, max_length=5000)
    event_id: str | None = Field(default=None, min_length=1, max_length=500)
    contract_version: str = CONTRACT_VERSION


class WorkProposalDecide(BaseModel):
    action: Literal["create_task", "link", "merge", "defer", "reject"]
    reason: str | None = Field(default=None, max_length=5000)
    task_id: uuid.UUID | None = None           # link
    merge_into_id: uuid.UUID | None = None     # merge
    title: str | None = Field(default=None, min_length=1, max_length=500)   # create_task
    task_type_key: str = "task"


class WorkProposalVersionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    version: int
    basis_revision: str
    verification_plan_object_id: uuid.UUID | None
    verification_plan_revision: str | None
    expected_output: str
    result_scope: str | None
    reason: str
    created_at: datetime


class WorkProposalResponse(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    stage: str
    work_kind: str
    basis: ObjectResponse
    work_scope_key: str
    status: str
    task_id: uuid.UUID | None
    merged_into_id: uuid.UUID | None
    decision_reason: str | None
    decided_by: uuid.UUID | None
    decided_at: datetime | None
    current_version: int
    updated_since_decision: bool
    versions: list[WorkProposalVersionResponse]
    created_at: datetime


class WorkProposalImportResult(BaseModel):
    proposal: WorkProposalResponse
    created: bool        # a new proposal (not a repeat / a new version)
    new_version: bool
    replayed: bool


# ── Delivery and recipient acceptance (TT-21) ────────────────────────────────

class AcceptanceWithdraw(BaseModel):
    reason: str = Field(min_length=1, max_length=5000)


class RecipientAcceptanceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    delivery_id: uuid.UUID | None
    proposal_id: uuid.UUID | None
    work_package_id: uuid.UUID | None
    recipient: str
    usage_scope: str | None
    accepted_by: str
    accepted_at: datetime
    authority: str | None
    source: str
    ref: str | None
    note: str | None
    fact_revision_id: uuid.UUID | None
    status: str
    historical: bool
    recorded_by: uuid.UUID | None
    withdrawn_at: datetime | None
    withdrawal_reason: str | None
    created_at: datetime


class DeliveryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    task_id: uuid.UUID
    proposal_id: uuid.UUID
    work_package_id: uuid.UUID | None
    target: str
    ref: str | None
    note: str | None
    proposed_by: uuid.UUID
    created_at: datetime
    is_current: bool = False
    acceptances: list[RecipientAcceptanceResponse] = []


class DeliveriesView(BaseModel):
    deliveries: list[DeliveryResponse]
    historical: list[RecipientAcceptanceResponse]   # manual records without a binding
