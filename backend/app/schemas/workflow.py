import uuid
from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from app.models.workflow import StatusCategory, ViewType


# ── Views ─────────────────────────────────────────────────────────────────────

class ViewCreate(BaseModel):
    name: str
    type: ViewType
    position: int | None = None


class ViewUpdate(BaseModel):
    name: str | None = None
    position: int | None = None


class ViewResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    project_id: uuid.UUID
    name: str
    type: ViewType
    position: int
    is_default: bool
    created_at: datetime
    updated_at: datetime


# ── Board columns ─────────────────────────────────────────────────────────────

class BoardColumnCreate(BaseModel):
    name: str
    position: int = 0


class BoardColumnUpdate(BaseModel):
    name: str | None = None
    position: int | None = None


class BoardColumnResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    view_id: uuid.UUID
    name: str
    position: int
    status_ids: list[uuid.UUID] = []
    created_at: datetime
    updated_at: datetime


class AddStatusToColumn(BaseModel):
    status_id: uuid.UUID


# ── Task type configs ─────────────────────────────────────────────────────────

class SetTaskTypeWorkflow(BaseModel):
    workflow_id: uuid.UUID


class TaskTypeConfigResponse(BaseModel):
    task_type_id: uuid.UUID
    task_type_key: str
    task_type_name: str
    workflow_id: uuid.UUID | None
    workflow_name: str | None
    is_project_override: bool


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
    category: StatusCategory | None = None
    position: int | None = None
    is_default: bool | None = None
    color: str | None = None


class MigrateStatus(BaseModel):
    target_status_id: uuid.UUID


_FIELD = Annotated[str, StringConstraints(pattern=r"^[A-Za-z_][A-Za-z0-9_]{0,63}$")]


class TransitionCreate(BaseModel):
    from_status_id: uuid.UUID
    to_status_id: uuid.UUID
    required_role: str | None = None
    required_fields: list[_FIELD] = Field(default_factory=list, max_length=50)


class TransitionUpdate(BaseModel):
    required_role: str | None = None
    required_fields: list[_FIELD] | None = Field(default=None, max_length=50)


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
    required_fields: list[str] = []
    created_at: datetime
    updated_at: datetime


class WorkflowResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    project_id: uuid.UUID | None
    name: str
    is_default: bool
    created_at: datetime
    updated_at: datetime
    statuses: list[StatusResponse] = []
    transitions: list[TransitionResponse] = []
