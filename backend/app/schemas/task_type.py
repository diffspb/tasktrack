import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class TaskTypeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    key: str
    name: str
    is_system: bool
    color: str | None
    icon: str | None
    created_at: datetime
    updated_at: datetime
