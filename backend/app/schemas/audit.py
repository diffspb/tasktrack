import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, computed_field

from app.services.audit_service import encode_cursor


class AuditEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    xid: int = Field(exclude=True)
    occurred_at: datetime
    actor_id: uuid.UUID | None
    project_id: uuid.UUID | None
    task_id: uuid.UUID | None
    session_id: uuid.UUID | None = None
    entity_type: str
    entity_id: uuid.UUID
    action: str
    reason: str | None
    before: dict | None
    after: dict | None

    @computed_field
    @property
    def cursor(self) -> str:
        return encode_cursor(self)


class AuditPage(BaseModel):
    items: list[AuditEventResponse]
    # Pass as `after` to continue; unchanged when there is nothing new.
    next_cursor: str | None
