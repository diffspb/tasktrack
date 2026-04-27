from typing import Any

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.db import get_session


async def get_current_user(
    session: AsyncSession = Depends(get_session),  # noqa: ARG001
) -> Any:
    if settings.auth_stub:
        from app.core.auth_stub import STUB_USER

        return STUB_USER
    # Phase 1+: replace StubUser with real ORM User + Keycloak JWT validation
    from fastapi import HTTPException, status

    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Keycloak auth not configured",
    )
