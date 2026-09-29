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
    from sqlalchemy.ext.asyncio import async_sessionmaker

    from app.core.db import _FTS_DDL
    from app.models.task_type import TaskType

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

    # Seed system task types (shared across all tests, never rolled back)
    Session = async_sessionmaker(engine, expire_on_commit=False)
    async with Session() as session:
        for key, name, icon, color in [
            ("task",     "Задача",  "check-square", "#6366f1"),
            ("bug",      "Баг",     "bug",          "#ef4444"),
            ("story",    "История", "book-open",    "#10b981"),
            ("epic",     "Эпик",    "zap",          "#f59e0b"),
            ("decision", "Decision","git-branch",   "#8b5cf6"),
        ]:
            session.add(TaskType(key=key, name=name, is_system=True, icon=icon, color=color))
        await session.commit()

    yield engine
    await engine.dispose()


# ---------------------------------------------------------------------------
# Fresh databases for tests that need real commits or run Alembic
# (concurrency, migrations). Created in the same container, dropped afterwards.
# ---------------------------------------------------------------------------

def _server_url(pg) -> str:
    host = pg.get_container_host_ip()
    port = pg.get_exposed_port(5432)
    return f"postgresql+asyncpg://{pg.username}:{pg.password}@{host}:{port}"


async def run_alembic(url: str, command_name: str, *args: str) -> None:
    """Run an alembic command against `url` in a worker thread (env.py calls asyncio.run)."""
    import asyncio
    from pathlib import Path

    from alembic import command
    from alembic.config import Config

    cfg = Config(str(Path(__file__).parent.parent / "alembic.ini"))
    cfg.attributes["database_url"] = url
    await asyncio.to_thread(getattr(command, command_name), cfg, *args)


@pytest.fixture(scope="session")
def alembic():
    """`await alembic(url, "upgrade", "head")`."""
    return run_alembic


@pytest_asyncio.fixture(scope="module")
async def make_database(postgres_container):
    """Factory: `url = await make_database()` creates an empty database."""
    import uuid

    from sqlalchemy import text

    base = _server_url(postgres_container)
    admin = create_async_engine(f"{base}/{postgres_container.dbname}", isolation_level="AUTOCOMMIT")
    created: list[str] = []

    async def factory() -> str:
        name = f"t_{uuid.uuid4().hex[:10]}"
        async with admin.connect() as conn:
            await conn.execute(text(f"CREATE DATABASE {name}"))
        created.append(name)
        return f"{base}/{name}"

    yield factory

    async with admin.connect() as conn:
        for name in created:
            await conn.execute(text(f"DROP DATABASE IF EXISTS {name} WITH (FORCE)"))
    await admin.dispose()


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
