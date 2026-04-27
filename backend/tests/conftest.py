import uuid

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.api.deps import get_current_user, get_session
from app.core.auth_stub import STUB_USER_ID
from app.main import app
from app.models import Base
from app.models.user import User

_TEST_DB_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture(scope="session", loop_scope="session")
async def async_engine():
    engine = create_async_engine(_TEST_DB_URL)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(async_engine) -> AsyncSession:
    session_maker = async_sessionmaker(async_engine, expire_on_commit=False)
    async with session_maker() as session:
        yield session


@pytest_asyncio.fixture
async def stub_user(db_session: AsyncSession) -> User:
    user = await db_session.get(User, STUB_USER_ID)
    if not user:
        user = User(
            id=STUB_USER_ID,
            email="dev@localhost",
            display_name="Dev User",
            keycloak_id=str(STUB_USER_ID),
            is_active=True,
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def client(db_session: AsyncSession, stub_user: User) -> AsyncClient:
    async def override_get_session():
        yield db_session

    def override_get_current_user():
        return stub_user

    app.dependency_overrides[get_session] = override_get_session
    app.dependency_overrides[get_current_user] = override_get_current_user

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac

    app.dependency_overrides.clear()
