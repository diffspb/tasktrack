"""Dev-only helpers, available when AUTH_STUB=true."""
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth_stub import list_stub_users
from app.core.config import settings
from app.core.db import get_session

router = APIRouter(tags=["dev"])


class StubUserRow(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str
    display_name: str


@router.get("/dev/stub-users", response_model=list[StubUserRow])
async def get_stub_users(session: AsyncSession = Depends(get_session)):
    if not settings.auth_stub:
        raise HTTPException(status.HTTP_404_NOT_FOUND)
    return await list_stub_users(session)
