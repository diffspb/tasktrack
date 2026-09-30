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
from sqlalchemy import select, text
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


async def test_solution_comments_become_historical_proposals(make_database, alembic):
    """a8c6e3f0d4b2: live `solution` comments → proposals `historical`, meta cleaned."""
    import uuid

    from sqlalchemy.ext.asyncio import async_sessionmaker

    from app.models.comment import Comment
    from app.models.result import ResultProposal
    from app.models.task import Task
    from app.models.task_type import TaskType
    from app.models.user import User
    from app.schemas.project import ProjectCreate
    from app.schemas.task import TaskCreate
    from app.services import project_service, task_service

    url = await make_database()
    await alembic(url, "upgrade", "head")
    engine = create_async_engine(url)
    Session = async_sessionmaker(engine, expire_on_commit=False)
    async with Session() as s:
        s.add(TaskType(key="task", name="Задача", is_system=True))
        user = User(id=uuid.uuid4(), email="m@t.com", display_name="M",
                    keycloak_id=str(uuid.uuid4()), is_active=True)
        s.add(user)
        await s.flush()
        project = await project_service.create_project(s, ProjectCreate(name="Mig", key="MIG"), user)
        task = await task_service.create_task(s, project.id, TaskCreate(title="T"), user)
        task_id = task.id

    await alembic(url, "downgrade", "f7b5d2e9c3a1")
    async with engine.begin() as conn:
        live = uuid.uuid4()
        await conn.execute(text(
            "INSERT INTO comments (id, task_id, author_id, content, labels, created_at, updated_at) "
            "VALUES (:id, :t, :a, 'Мой вариант', ARRAY['solution'], now(), now()), "
            "       (gen_random_uuid(), :t, :a, 'Просто комментарий', ARRAY[]::varchar[], now(), now())"
        ), {"id": live, "t": task_id, "a": user.id})
        await conn.execute(text(
            "UPDATE tasks SET meta = jsonb_build_object('solution_comment_id', CAST(:c AS text)) WHERE id = :t"
        ), {"c": str(live), "t": task_id})
    await alembic(url, "upgrade", "head")

    async with Session() as s:
        proposals = (await s.scalars(select(ResultProposal).where(ResultProposal.task_id == task_id))).all()
        assert len(proposals) == 1
        p = proposals[0]
        assert p.status.value == "historical" and p.summary == "Мой вариант"
        assert p.provenance["migrated_from_comment"] == str(live)
        task = await s.get(Task, task_id)
        assert task.result_state == "historical" and "solution_comment_id" not in task.meta
        assert (await s.get(Comment, live)) is not None  # комментарий остаётся обсуждением
    await engine.dispose()


async def test_legacy_delivery_bound_and_acceptance_historical(make_database, alembic):
    """d8f2a6c4e1b9 (ADR-024): Task.delivery names its proposal → a Delivery row; a manual
    recipient acceptance has no binding → a historical record, its version is not guessed."""
    import uuid

    from sqlalchemy.ext.asyncio import async_sessionmaker

    from app.models.portfolio import Delivery, RecipientAcceptance
    from app.models.result import ProposalStatus, ResultProposal
    from app.models.task import Task
    from app.models.task_type import TaskType
    from app.models.user import User
    from app.schemas.project import ProjectCreate
    from app.schemas.task import TaskCreate
    from app.services import project_service, task_service

    url = await make_database()
    await alembic(url, "upgrade", "head")
    engine = create_async_engine(url)
    Session = async_sessionmaker(engine, expire_on_commit=False)
    async with Session() as s:
        s.add(TaskType(key="task", name="Задача", is_system=True))
        user = User(id=uuid.uuid4(), email="d@t.com", display_name="D",
                    keycloak_id=str(uuid.uuid4()), is_active=True)
        s.add(user)
        await s.flush()
        project = await project_service.create_project(s, ProjectCreate(name="Del", key="DEL"), user)
        task = await task_service.create_task(s, project.id, TaskCreate(title="T"), user)
        proposal = ResultProposal(task_id=task.id, version=1, author_id=user.id,
                                  status=ProposalStatus.accepted, summary="готово")
        s.add(proposal)
        await s.commit()
        task_id, proposal_id = task.id, proposal.id

    await alembic(url, "downgrade", "c1e8a5b2f6d4")
    async with engine.begin() as conn:
        await conn.execute(text(
            "UPDATE tasks SET delivery = jsonb_build_object("
            "  'proposal_id', CAST(:p AS text), 'target', 'office:P-PACK', 'ref', 'OD-1', 'note', NULL,"
            "  'proposed_by', CAST(:u AS text), 'proposed_at', '2026-09-01T10:00:00+00:00'),"
            " recipient_acceptance = jsonb_build_object("
            "  'accepted_by', 'owner', 'accepted_at', '2026-09-02T10:00:00+00:00', 'source', 'email',"
            "  'ref', NULL, 'note', 'ок', 'recorded_by', CAST(:u AS text),"
            "  'recorded_at', '2026-09-02T11:00:00+00:00')"
            " WHERE id = :t"
        ), {"p": str(proposal_id), "u": str(user.id), "t": task_id})
    await alembic(url, "upgrade", "head")

    async with Session() as s:
        [delivery] = (await s.scalars(select(Delivery).where(Delivery.task_id == task_id))).all()
        assert delivery.proposal_id == proposal_id and delivery.target == "office:P-PACK"
        [acc] = (await s.scalars(select(RecipientAcceptance).where(RecipientAcceptance.task_id == task_id))).all()
        assert acc.historical and acc.delivery_id is None and acc.proposal_id is None
        assert acc.accepted_by == "owner" and acc.note == "ок"
        task = await s.get(Task, task_id)
        assert task.delivery["delivery_id"] == str(delivery.id)
        assert task.recipient_acceptance["accepted_by"] == "owner"   # the summary stays
    await engine.dispose()
