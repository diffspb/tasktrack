import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, field_validator

from app.models.project import ProjectMemberRole, ProjectVisibility


class ProjectCreate(BaseModel):
    name: str
    key: str
    description: str | None = None
    visibility: ProjectVisibility = ProjectVisibility.restricted

    @field_validator("key")
    @classmethod
    def normalize_key(cls, v: str) -> str:
        return v.upper().strip()


class ProjectUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    version: int


class ProjectMemberAdd(BaseModel):
    user_id: uuid.UUID
    role: ProjectMemberRole = ProjectMemberRole.member


class ProjectMemberResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    project_id: uuid.UUID
    user_id: uuid.UUID
    role: ProjectMemberRole
    created_at: datetime


class ProjectResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    key: str
    description: str | None
    visibility: ProjectVisibility
    owner_id: uuid.UUID
    is_archived: bool
    version: int
    created_at: datetime
    updated_at: datetime
    members: list[ProjectMemberResponse] = []
