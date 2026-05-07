import re
import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, field_validator

from app.models.project import ProjectMemberRole, ProjectVisibility

_KEY_RE = re.compile(r'^[A-Z0-9][A-Z0-9\-]{0,8}[A-Z0-9]$|^[A-Z0-9]$')


class ProjectCreate(BaseModel):
    name: str
    key: str
    description: str | None = None
    visibility: ProjectVisibility = ProjectVisibility.restricted

    @field_validator("key")
    @classmethod
    def normalize_key(cls, v: str) -> str:
        v = v.upper().strip()
        if not _KEY_RE.match(v):
            raise ValueError("Project key must be 1-10 uppercase alphanumeric characters or hyphens")
        return v


class ProjectUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    visibility: ProjectVisibility | None = None
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


class _UserSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    display_name: str
    email: str


class ProjectMemberWithUser(BaseModel):
    """Member row with inline user info — for UI pickers."""

    user: _UserSummary
    role: ProjectMemberRole


class ProjectMembersListResponse(BaseModel):
    items: list[ProjectMemberWithUser]


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
