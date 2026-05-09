import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.task import TaskPriority
from app.schemas.link_type import LinkTypeResponse


class TaskTypeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    key: str
    name: str
    is_system: bool
    color: str | None
    icon: str | None


class TaskCreate(BaseModel):
    title: str
    description: str | None = None
    task_type_key: str = "task"
    priority: TaskPriority = TaskPriority.medium
    workflow_id: uuid.UUID | None = None
    assignee_id: uuid.UUID | None = None
    parent_task_id: uuid.UUID | None = None
    start_date: date | None = None
    due_date: date | None = None
    duration_days: int | None = None
    meta: dict = Field(default_factory=dict)


class TaskUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    priority: TaskPriority | None = None
    assignee_id: uuid.UUID | None = None
    start_date: date | None = None
    due_date: date | None = None
    duration_days: int | None = None
    meta: dict | None = None
    version: int


class TaskStatusTransition(BaseModel):
    status_id: uuid.UUID


class TaskMinimal(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    key: str
    title: str
    task_type: TaskTypeResponse | None = None


class TaskLinkCreate(BaseModel):
    target_task_id: uuid.UUID
    link_type_id: uuid.UUID


class TaskLinkResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    source_task: TaskMinimal
    target_task: TaskMinimal
    link_type_id: uuid.UUID
    link_type: LinkTypeResponse
    created_at: datetime


class TaskResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    key: str
    project_id: uuid.UUID
    workflow_id: uuid.UUID
    task_type_id: uuid.UUID
    task_type: TaskTypeResponse | None = None
    reporter_id: uuid.UUID
    assignee_id: uuid.UUID | None
    parent_task_id: uuid.UUID | None
    current_status_id: uuid.UUID
    title: str
    description: str | None
    priority: TaskPriority
    meta: dict
    start_date: date | None
    due_date: date | None
    duration_days: int | None
    version: int
    deleted_at: datetime | None
    created_at: datetime
    updated_at: datetime
