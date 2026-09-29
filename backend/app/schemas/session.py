import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class SessionCreate(BaseModel):
    # executor — exclusive per task; reviewer — checking a result, may run alongside.
    role: Literal["executor", "reviewer"] = "executor"
    machine: str | None = Field(default=None, max_length=200)
    workdir: str | None = Field(default=None, max_length=1000)
    client: str | None = Field(default=None, max_length=200)  # e.g. agent / console name


class CheckpointCreate(BaseModel):
    note: str = Field(min_length=1, max_length=5000)
    data: dict = Field(default_factory=dict)


class SessionComplete(BaseModel):
    result: str | None = Field(default=None, max_length=20000)


class SessionRelease(BaseModel):
    reason: str = Field(max_length=5000)

    @field_validator("reason")
    @classmethod
    def reason_required(cls, v: str) -> str:
        # Release is an explicit decision: e.g. "the process was checked and stopped".
        if not v.strip():
            raise ValueError("reason is required")
        return v.strip()


class CheckpointResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    note: str
    data: dict
    created_at: datetime


class SessionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    task_id: uuid.UUID
    user_id: uuid.UUID
    work_package_id: uuid.UUID | None
    role: str
    state: str
    machine: str | None
    workdir: str | None
    client: str | None
    created_at: datetime
    last_checkpoint_at: datetime | None
    ended_at: datetime | None
    ended_by: uuid.UUID | None
    end_reason: str | None
    result: str | None
    checkpoints: list[CheckpointResponse] = []
