import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from testcontainers.postgres import PostgresContainer

from app.api.deps import get_current_user, get_session
from app.core.auth_stub import STUB_USER_ID
from app.main import app
from app.models import Base
from app.models.user import User


# ---------------------------------------------------------------------------
# Session-scoped: one PostgreSQL container + schema for the whole test run
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def postgres_container():
    with PostgresContainer("postgres:16-alpine") as pg:
        yield pg


@pytest_asyncio.fixture(scope="session", loop_scope="session")
async def async_engine(postgres_container):
    from sqlalchemy import text

    from app.core.db import _FTS_DDL

    host = postgres_container.get_container_host_ip()
    port = postgres_container.get_exposed_port(5432)
    url = (
        f"postgresql+asyncpg://{postgres_container.username}"
        f":{postgres_container.password}"
        f"@{host}:{port}/{postgres_container.dbname}"
    )
    engine = create_async_engine(url)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        for stmt in _FTS_DDL:
            await conn.execute(text(stmt))
    yield engine
    await engine.dispose()


# ---------------------------------------------------------------------------
# Function-scoped: each test wraps in a transaction rolled back after.
# join_transaction_mode="create_savepoint" makes session.commit() issue a
# SAVEPOINT instead of COMMIT, so the outer rollback undoes everything.
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture
async def db_session(async_engine) -> AsyncSession:
    async with async_engine.connect() as conn:
        await conn.begin()
        session = AsyncSession(
            bind=conn,
            join_transaction_mode="create_savepoint",
            expire_on_commit=False,
        )
        yield session
        await session.close()
        await conn.rollback()


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
        await db_session.flush()
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
