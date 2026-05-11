from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.db import get_session

_bearer = HTTPBearer(auto_error=False)


async def get_current_user(
    request: Request,
    session: AsyncSession = Depends(get_session),
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
):
    if settings.auth_stub:
        from app.core.auth_stub import get_or_create_stub_user

        email = request.headers.get("x-stub-user") or None
        return await get_or_create_stub_user(session, email=email)

    if not credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    from app.core.auth import validate_token
    from app.models.user import User

    payload = validate_token(credentials.credentials)

    keycloak_id: str = payload["sub"]
    email: str = payload.get("email", "")
    display_name: str = payload.get("preferred_username") or email

    user = await session.scalar(select(User).where(User.keycloak_id == keycloak_id))
    if user is None:
        existing_count = await session.scalar(select(func.count()).select_from(User))
        is_first = existing_count == 0
        user = User(
            keycloak_id=keycloak_id, email=email, display_name=display_name,
            is_active=True, is_superuser=is_first,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
    elif user.email != email or user.display_name != display_name:
        user.email = email
        user.display_name = display_name
        await session.commit()

    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is inactive")

    return user
