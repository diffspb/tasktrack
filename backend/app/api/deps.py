from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.db import get_session


async def get_current_user(session: AsyncSession = Depends(get_session)):
    if settings.auth_stub:
        from app.core.auth_stub import get_or_create_stub_user

        return await get_or_create_stub_user(session)

    from fastapi import HTTPException, status

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not authenticated",
    )
