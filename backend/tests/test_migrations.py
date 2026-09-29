"""Alembic-миграции (FR-003, TT-07).

- схема после `upgrade head` совпадает с моделями: изменил модель — нужна ревизия;
- полный откат и повторный накат проходят;
- одновременный старт нескольких процессов не запускает конфликтующие миграции.
"""
import asyncio
import os
import sys
from pathlib import Path

from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

import app.models  # noqa: F401 — registers all models
from app.core.db import FTS_MANAGED_INDEXES
from app.models.base import Base

BACKEND_DIR = Path(__file__).parent.parent


def _include(obj, name, type_, reflected, compare_to) -> bool:
    return not (type_ == "index" and name in FTS_MANAGED_INDEXES)


async def _schema_diff(url: str) -> list:
    engine = create_async_engine(url)
    async with engine.connect() as conn:
        diff = await conn.run_sync(
            lambda c: compare_metadata(
                MigrationContext.configure(c, opts={"include_object": _include}), Base.metadata
            )
        )
    await engine.dispose()
    return diff


async def _head(url: str) -> str | None:
    engine = create_async_engine(url)
    async with engine.connect() as conn:
        rev = await conn.scalar(text("SELECT version_num FROM alembic_version"))
    await engine.dispose()
    return rev


async def test_migrations_match_models(make_database, alembic):
    url = await make_database()
    await alembic(url, "upgrade", "head")
    assert await _schema_diff(url) == []


async def test_full_downgrade_and_upgrade(make_database, alembic):
    url = await make_database()
    await alembic(url, "upgrade", "head")
    await alembic(url, "downgrade", "base")
    await alembic(url, "upgrade", "head")
    assert await _schema_diff(url) == []


async def _upgrade_in_process(url: str) -> tuple[int, str]:
    """Separate OS process, as on a real multi-worker start (alembic keeps global state)."""
    proc = await asyncio.create_subprocess_exec(
        sys.executable, "-m", "alembic", "upgrade", "head",
        cwd=BACKEND_DIR, env={**os.environ, "DATABASE_URL": url},
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT,
    )
    out, _ = await asyncio.wait_for(proc.communicate(), timeout=60)
    return proc.returncode, out.decode()


async def test_concurrent_startup_migrates_once(make_database):
    url = await make_database()
    results = await asyncio.gather(*(_upgrade_in_process(url) for _ in range(3)))
    failed = [out for code, out in results if code != 0]
    assert failed == []
    assert await _head(url) is not None
    assert await _schema_diff(url) == []
