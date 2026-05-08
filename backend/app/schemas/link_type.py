from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, ConfigDict, field_validator


class LinkTypeCreate(BaseModel):
    name: str
    outward_name: str
    inward_name: str
    is_directed: bool = True
    color: str | None = None
    constraint: dict | None = None
    position: int = 0

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        v = v.strip().lower().replace(" ", "_")
        if not v:
            raise ValueError("name must not be empty")
        return v


class LinkTypeUpdate(BaseModel):
    outward_name: str | None = None
    inward_name: str | None = None
    is_directed: bool | None = None
    color: str | None = None
    constraint: dict | None = None
    position: int | None = None
    is_active: bool | None = None


class LinkTypeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    outward_name: str
    inward_name: str
    is_directed: bool
    color: str | None
    constraint: dict | None
    position: int
    is_active: bool
    created_at: datetime
    updated_at: datetime
