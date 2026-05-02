from collections.abc import AsyncGenerator

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings

engine = create_async_engine(settings.database_url, echo=False)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with SessionLocal() as session:
        yield session


# Postgres-side machinery for full-text search on Task.search_vector.
# Configuration: 'russian' (snowball). Trigger keeps the column in sync
# with title || description on every insert/update.
_FTS_DDL = [
    """
    CREATE OR REPLACE FUNCTION tasks_search_vector_update() RETURNS trigger AS $$
    BEGIN
      NEW.search_vector :=
        to_tsvector('russian',
          coalesce(NEW.title, '') || ' ' || coalesce(NEW.description, ''));
      RETURN NEW;
    END
    $$ LANGUAGE plpgsql
    """,
    """
    DROP TRIGGER IF EXISTS tasks_search_vector_trigger ON tasks
    """,
    """
    CREATE TRIGGER tasks_search_vector_trigger
    BEFORE INSERT OR UPDATE OF title, description ON tasks
    FOR EACH ROW EXECUTE FUNCTION tasks_search_vector_update()
    """,
    """
    CREATE INDEX IF NOT EXISTS ix_tasks_search_vector
    ON tasks USING GIN (search_vector)
    """,
]


async def create_tables() -> None:
    from app.models import Base  # noqa: F401 — side-effect import registers all models

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        for stmt in _FTS_DDL:
            await conn.execute(text(stmt))
