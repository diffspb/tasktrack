from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.db import get_session


async def get_current_user(
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    if settings.auth_stub:
        from app.core.auth_stub import get_or_create_stub_user

        # Dev "View as" switch: client may pass X-Stub-User: <email>.
        # Ignored when AUTH_STUB is off.
        email = request.headers.get("x-stub-user") or None
        return await get_or_create_stub_user(session, email=email)

    from fastapi import HTTPException, status

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not authenticated",
    )
