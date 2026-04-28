import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.workflow import StatusCategory


class WorkflowCreate(BaseModel):
    name: str
    is_default: bool = False


class WorkflowUpdate(BaseModel):
    name: str | None = None
    is_default: bool | None = None


class StatusCreate(BaseModel):
    name: str
    category: StatusCategory
    is_default: bool = False
    position: int = 0
    color: str | None = None


class StatusUpdate(BaseModel):
    name: str | None = None
    position: int | None = None
    is_default: bool | None = None
    color: str | None = None


class MigrateStatus(BaseModel):
    target_status_id: uuid.UUID


class TransitionCreate(BaseModel):
    from_status_id: uuid.UUID
    to_status_id: uuid.UUID
    required_role: str | None = None


class StatusResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    workflow_id: uuid.UUID
    name: str
    category: StatusCategory
    is_default: bool
    position: int
    color: str | None
    created_at: datetime
    updated_at: datetime


class TransitionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    workflow_id: uuid.UUID
    from_status_id: uuid.UUID
    to_status_id: uuid.UUID
    required_role: str | None
    created_at: datetime
    updated_at: datetime


class WorkflowResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    project_id: uuid.UUID
    name: str
    is_default: bool
    created_at: datetime
    updated_at: datetime
    statuses: list[StatusResponse] = []
    transitions: list[TransitionResponse] = []
