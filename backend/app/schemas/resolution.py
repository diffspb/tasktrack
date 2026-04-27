import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ResolutionCreate(BaseModel):
    name: str
    is_default: bool = False
    position: int = 0


class ResolutionUpdate(BaseModel):
    name: str | None = None
    is_default: bool | None = None
    position: int | None = None


class ResolutionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    project_id: uuid.UUID
    name: str
    is_default: bool
    position: int
    created_at: datetime
    updated_at: datetime
