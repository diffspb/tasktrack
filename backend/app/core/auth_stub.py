"""
Auth stub for AUTH_STUB=true. Returns a deterministic User from the seed
database. Supports a dev "View as" switch via the X-Stub-User HTTP header
(value: user email).
"""
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

# Default stub identity — used by tests (matches the legacy id) and as a
# fallback when seed has not run yet.
STUB_USER_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")
DEFAULT_STUB_EMAIL = "admin@localhost"


async def get_or_create_stub_user(
    session: AsyncSession, email: str | None = None,
):
    """Resolve the stub user.

    - email=None  → DEFAULT_STUB_EMAIL (or create a placeholder if DB is empty).
    - email set   → look up by email; 401 if not found, so a typo in the
                    dev switcher fails loud rather than silently.
    """
    from fastapi import HTTPException, status

    from app.models.user import User

    target_email = email or DEFAULT_STUB_EMAIL

    user = await session.scalar(select(User).where(User.email == target_email))
    if user:
        return user

    if email is not None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Stub user with email '{email}' not found",
        )

    # Pre-seed bootstrap: keep legacy behavior so /health works on a fresh DB.
    user = await session.get(User, STUB_USER_ID)
    if not user:
        user = User(
            id=STUB_USER_ID,
            email=DEFAULT_STUB_EMAIL,
            display_name="Admin",
            keycloak_id=str(STUB_USER_ID),
            is_active=True,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
    return user


async def list_stub_users(session: AsyncSession):
    """All active users — used by the dev switcher dropdown."""
    from app.models.user import User

    rows = await session.scalars(
        select(User).where(User.is_active.is_(True)).order_by(User.email)
    )
    return list(rows.all())
