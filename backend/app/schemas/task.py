import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict

from app.models.task import AssigneeRole, GlobalStatus, TaskPriority, TaskType


class TaskCreate(BaseModel):
    title: str
    description: str | None = None
    task_type: TaskType = TaskType.task
    priority: TaskPriority = TaskPriority.medium
    workflow_id: uuid.UUID
    decision_maker_id: uuid.UUID | None = None
    due_date: date | None = None
    allow_multi_accept: bool = False


class TaskUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    priority: TaskPriority | None = None
    decision_maker_id: uuid.UUID | None = None
    due_date: date | None = None
    allow_multi_accept: bool | None = None
    version: int


class AssignmentCreate(BaseModel):
    user_id: uuid.UUID
    role: AssigneeRole = AssigneeRole.lead


class AssignmentTransition(BaseModel):
    status_id: uuid.UUID
    resolution_id: uuid.UUID | None = None


class AssignmentRoleUpdate(BaseModel):
    role: AssigneeRole


class AssignmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    task_id: uuid.UUID
    user_id: uuid.UUID
    role: AssigneeRole
    current_status_id: uuid.UUID
    resolution_id: uuid.UUID | None
    created_at: datetime
    updated_at: datetime


class TaskResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    key: str
    project_id: uuid.UUID
    workflow_id: uuid.UUID
    reporter_id: uuid.UUID
    decision_maker_id: uuid.UUID | None
    title: str
    description: str | None
    task_type: TaskType
    priority: TaskPriority
    global_status: GlobalStatus
    due_date: date | None
    allow_multi_accept: bool
    version: int
    deleted_at: datetime | None
    created_at: datetime
    updated_at: datetime
    assignments: list[AssignmentResponse] = []
