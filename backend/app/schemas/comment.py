import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class CommentCreate(BaseModel):
    content: str
    parent_comment_id: uuid.UUID | None = None
    labels: list[str] = []


class CommentUpdate(BaseModel):
    content: str


class CommentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    task_id: uuid.UUID
    author_id: uuid.UUID
    parent_comment_id: uuid.UUID | None
    content: str
    labels: list[str]
    edited_at: datetime | None
    deleted_at: datetime | None
    created_at: datetime
    updated_at: datetime
