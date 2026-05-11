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

    # Read superuser role from JWT:
    # client role  → resource_access.<client_id>.roles
    # realm role   → realm_access.roles  (fallback)
    client_roles: list = (
        payload.get("resource_access", {})
        .get(settings.keycloak_client_id, {})
        .get("roles", [])
    )
    realm_roles: list = payload.get("realm_access", {}).get("roles", [])
    is_superuser = "superuser" in client_roles or "superuser" in realm_roles

    user = await session.scalar(select(User).where(User.keycloak_id == keycloak_id))
    if user is None:
        user = User(
            keycloak_id=keycloak_id, email=email, display_name=display_name,
            is_active=True, is_superuser=is_superuser,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
    else:
        dirty = False
        if user.email != email or user.display_name != display_name:
            user.email = email
            user.display_name = display_name
            dirty = True
        if user.is_superuser != is_superuser:
            user.is_superuser = is_superuser
            dirty = True
        if dirty:
            await session.commit()

    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is inactive")

    return user
