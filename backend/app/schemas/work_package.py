import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

_KEY = r"^[a-z0-9][a-z0-9_-]{0,31}$"


class Criterion(BaseModel):
    # Stable key referenced by result proposals and reviews; assigned on issue if omitted.
    key: str | None = Field(default=None, pattern=_KEY)
    text: str = Field(min_length=1, max_length=2000)
    required: bool = True


class PackageInput(BaseModel):
    kind: str = Field(min_length=1, max_length=50)  # repo, document, artifact, dataset, requirement…
    ref: str = Field(min_length=1, max_length=1000)
    version: str | None = Field(default=None, max_length=200)
    note: str | None = Field(default=None, max_length=2000)


class WorkPackageContent(BaseModel):
    """Draft: every field optional; completeness is checked on issue."""

    goal: str | None = Field(default=None, max_length=5000)
    expected_result: str | None = Field(default=None, max_length=5000)
    criteria: list[Criterion] = Field(default_factory=list, max_length=100)
    inputs: list[PackageInput] = Field(default_factory=list, max_length=100)
    constraints: list[str] = Field(default_factory=list, max_length=100)
    specialization: str | None = Field(default=None, max_length=100)

    @field_validator("criteria")
    @classmethod
    def unique_keys(cls, v: list[Criterion]) -> list[Criterion]:
        keys = [c.key for c in v if c.key]
        if len(keys) != len(set(keys)):
            raise ValueError("criterion keys must be unique")
        return v


class WorkPackageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    task_id: uuid.UUID
    version: int
    content: dict
    digest: str
    issued_by: uuid.UUID
    created_at: datetime


class WorkPackageState(BaseModel):
    # none — no draft; draft — never issued; issued — draft equals current; draft_changed — needs reissue
    state: Literal["none", "draft", "issued", "draft_changed"]
    draft: dict | None
    current: WorkPackageResponse | None
