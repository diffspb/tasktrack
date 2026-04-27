import uuid

from sqlalchemy.ext.asyncio import AsyncSession

STUB_USER_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")


async def get_or_create_stub_user(session: AsyncSession):
    from app.models.user import User

    user = await session.get(User, STUB_USER_ID)
    if not user:
        user = User(
            id=STUB_USER_ID,
            email="dev@localhost",
            display_name="Dev User",
            keycloak_id=str(STUB_USER_ID),
            is_active=True,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
    return user
