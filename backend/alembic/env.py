import asyncio
from logging.config import fileConfig

from sqlalchemy import pool, text
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Register all models so autogenerate sees every table.
import app.models  # noqa: F401, E402
from app.models.base import Base  # noqa: E402

target_metadata = Base.metadata

# Arbitrary constant shared by every TaskTrack process ("TTMIGRAT" in ASCII).
_MIGRATION_LOCK_KEY = 0x54544D4947524154


def include_object(obj, name, type_, reflected, compare_to) -> bool:
    from app.core.db import FTS_MANAGED_INDEXES
    return not (type_ == "index" and name in FTS_MANAGED_INDEXES)


def _get_url() -> str:
    # Callers (tests, scripts) may target another database via Config.attributes.
    if config.attributes.get("database_url"):
        return config.attributes["database_url"]
    from app.core.config import settings
    return settings.database_url


def run_migrations_offline() -> None:
    context.configure(
        url=_get_url(),
        target_metadata=target_metadata,
        include_object=include_object,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(
        connection=connection, target_metadata=target_metadata, include_object=include_object
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    cfg_section = dict(config.get_section(config.config_ini_section, {}))
    cfg_section["sqlalchemy.url"] = _get_url()

    connectable = async_engine_from_config(
        cfg_section,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        # Several processes may start at once (workers, replicas): the session-level
        # advisory lock makes them migrate one after another; the rest find head applied.
        # Commit right away so alembic runs its own transaction, not inside ours.
        await connection.execute(text("SELECT pg_advisory_lock(:k)"), {"k": _MIGRATION_LOCK_KEY})
        await connection.commit()
        try:
            await connection.run_sync(do_run_migrations)
        finally:
            await connection.execute(text("SELECT pg_advisory_unlock(:k)"), {"k": _MIGRATION_LOCK_KEY})
            await connection.commit()
    await connectable.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
