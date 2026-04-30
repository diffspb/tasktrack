import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.decision import SolutionStatus
from app.models.task import GlobalStatus


# --- Solution ---

class SolutionCreate(BaseModel):
    content: str = ""


class SolutionUpdate(BaseModel):
    content: str


class SolutionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    assignment_id: uuid.UUID
    content: str
    status: SolutionStatus
    submitted_at: datetime | None
    revision_comment: str | None
    created_at: datetime
    updated_at: datetime


class SolutionTransitionResponse(BaseModel):
    """Response from submit/withdraw/request-revision actions."""
    id: uuid.UUID
    status: SolutionStatus
    submitted_at: datetime | None
    revision_comment: str | None
    task_transitioned_to: GlobalStatus | None


# --- Decision criteria ---

class DecisionCriteriaItem(BaseModel):
    description: str
    position: int = 0


class DecisionCriteriaReplace(BaseModel):
    items: list[DecisionCriteriaItem] = Field(default_factory=list)


class DecisionCriteriaResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    description: str
    position: int
    is_locked: bool


class DecisionCriteriaListResponse(BaseModel):
    items: list[DecisionCriteriaResponse]


# --- Decision ---

class DecisionCreate(BaseModel):
    accepted_solution_ids: list[uuid.UUID] = Field(min_length=1)
    note: str | None = None


class DecisionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    task_id: uuid.UUID
    decision_maker_id: uuid.UUID
    accepted_solution_ids: list[uuid.UUID]
    note: str | None
    decided_at: datetime


# --- Revision ---

class RevisionRequest(BaseModel):
    feedback: str = Field(min_length=1)


# --- Close ---

class TaskCloseRequest(BaseModel):
    pass
