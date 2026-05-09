import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class GanttChartCreate(BaseModel):
    name: str
    description: str | None = None


class GanttChartUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    settings: dict | None = None
    position: int | None = None


class GanttChartResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    owner_id: uuid.UUID
    name: str
    description: str | None
    settings: dict
    position: int
    created_at: datetime
    updated_at: datetime


class GanttChartAddTask(BaseModel):
    task_id: uuid.UUID
