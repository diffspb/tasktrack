"""Конкурентные изменения задач (FR-003, TT-02 и TT-03).

Savepoint-изоляция из conftest держит все запросы теста в одном соединении,
поэтому гонку там не воспроизвести. Здесь — отдельная база в том же контейнере,
схема строится Alembic-миграциями, данные коммитятся по-настоящему, каждый
«клиент» работает в своей сессии и транзакции.
"""
import asyncio
import uuid

import pytest
import pytest_asyncio
from fastapi import HTTPException
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.config import settings
from app.models.project import Project
from app.models.task import Task
from app.models.task_type import TaskType
from app.models.user import User
from app.models.workflow import Status, Workflow
from app.schemas.project import ProjectCreate
from app.schemas.task import TaskCreate, TaskStatusTransition, TaskUpdate
from app.services import project_service, task_service


async def _alembic(url: str, *args: str) -> None:
    """Run an alembic command against `url` (env.py reads settings.database_url)."""
    from pathlib import Path

    from alembic import command
    from alembic.config import Config

    cfg = Config(str(Path(__file__).parent.parent / "alembic.ini"))
    original = settings.database_url
    settings.database_url = url
    try:
        await asyncio.to_thread(getattr(command, args[0]), cfg, *args[1:])
    finally:
        settings.database_url = original


@pytest_asyncio.fixture(scope="module")
async def committed(postgres_container):
    """Fresh database migrated to head; yields (url, sessionmaker)."""
    host = postgres_container.get_container_host_ip()
    port = postgres_container.get_exposed_port(5432)
    base = (
        f"postgresql+asyncpg://{postgres_container.username}"
        f":{postgres_container.password}@{host}:{port}"
    )
    dbname = f"concurrency_{uuid.uuid4().hex[:8]}"
    admin = create_async_engine(f"{base}/{postgres_container.dbname}", isolation_level="AUTOCOMMIT")
    async with admin.connect() as conn:
        await conn.execute(text(f"CREATE DATABASE {dbname}"))

    url = f"{base}/{dbname}"
    await _alembic(url, "upgrade", "head")

    engine = create_async_engine(url)
    Session = async_sessionmaker(engine, expire_on_commit=False)
    async with Session() as s:
        s.add(TaskType(key="task", name="Задача", is_system=True))
        await s.commit()

    yield url, Session

    await engine.dispose()
    async with admin.connect() as conn:
        await conn.execute(text(f"DROP DATABASE {dbname} WITH (FORCE)"))
    await admin.dispose()


async def _seed(Session) -> dict:
    async with Session() as s:
        user = User(
            id=uuid.uuid4(), email=f"c_{uuid.uuid4().hex[:8]}@t.com", display_name="C",
            keycloak_id=str(uuid.uuid4()), is_active=True,
        )
        s.add(user)
        await s.flush()
        project = await project_service.create_project(
            s, ProjectCreate(name="Race", key=uuid.uuid4().hex[:8].upper()), user
        )
        task = await task_service.create_task(
            s, project.id, TaskCreate(title="Race", assignee_id=user.id), user
        )
        wf = await s.scalar(
            select(Workflow).where(Workflow.project_id == project.id, Workflow.is_default.is_(True))
        )
        inprog = await s.scalar(
            select(Status).where(Status.workflow_id == wf.id, Status.name == "In Progress")
        )
        return {"user": user, "project_id": project.id, "task_id": task.id, "inprog_id": inprog.id}


async def _run_concurrently(Session, fn, n: int = 2) -> list:
    async def one(i: int):
        async with Session() as s:
            return await fn(s, i)
    return await asyncio.gather(*(one(i) for i in range(n)), return_exceptions=True)


# ── TT-02: атомарная проверка версии ────────────────────────────────────────

async def test_concurrent_updates_same_version_one_wins(committed):
    _, Session = committed
    ctx = await _seed(Session)

    results = await _run_concurrently(
        Session,
        lambda s, i: task_service.update_task(
            s, ctx["task_id"], TaskUpdate(title=f"writer-{i}", version=1), ctx["user"]
        ),
    )

    ok = [r for r in results if isinstance(r, Task)]
    conflicts = [r for r in results if isinstance(r, HTTPException) and r.status_code == 409]
    assert len(ok) == 1 and len(conflicts) == 1, results
    assert conflicts[0].detail["code"] == "VERSION_CONFLICT"

    async with Session() as s:
        task = await s.get(Task, ctx["task_id"])
        assert task.version == 2
        assert task.title == ok[0].title  # победившее обновление не потеряно


async def test_transition_and_update_same_version_one_wins(committed):
    _, Session = committed
    ctx = await _seed(Session)

    async def act(s, i):
        if i == 0:
            return await task_service.transition_status(
                s, ctx["task_id"], TaskStatusTransition(status_id=ctx["inprog_id"], version=1), ctx["user"]
            )
        return await task_service.update_task(
            s, ctx["task_id"], TaskUpdate(title="edited", version=1), ctx["user"]
        )

    results = await _run_concurrently(Session, act)
    conflicts = [r for r in results if isinstance(r, HTTPException) and r.status_code == 409]
    assert len(conflicts) == 1, results


# ── TT-03: атомарная нумерация ──────────────────────────────────────────────

async def test_concurrent_create_gives_unique_keys(committed):
    _, Session = committed
    ctx = await _seed(Session)  # уже создана задача №1

    results = await _run_concurrently(
        Session,
        lambda s, i: task_service.create_task(
            s, ctx["project_id"], TaskCreate(title=f"parallel-{i}"), ctx["user"]
        ),
        n=5,
    )

    assert all(isinstance(r, Task) for r in results), results
    numbers = sorted(int(r.key.rsplit("-", 1)[1]) for r in results)
    assert numbers == [2, 3, 4, 5, 6]


async def test_task_seq_migration_backfills_existing_projects(committed):
    """Обновление схемы с данными: счётчик продолжает нумерацию, а не начинает с 1."""
    url, Session = committed
    ctx = await _seed(Session)
    async with Session() as s:
        for i in range(2):
            await task_service.create_task(s, ctx["project_id"], TaskCreate(title=f"t{i}"), ctx["user"])
        # удалённая задача всё равно занимает свой номер
        t = await task_service.create_task(s, ctx["project_id"], TaskCreate(title="gone"), ctx["user"])
        await task_service.delete_task(s, t.id, ctx["user"])

    await _alembic(url, "downgrade", "-1")
    await _alembic(url, "upgrade", "head")

    async with Session() as s:
        project = await s.get(Project, ctx["project_id"])
        assert project.task_seq == 4
        new = await task_service.create_task(s, ctx["project_id"], TaskCreate(title="next"), ctx["user"])
        assert new.key == f"{project.key}-5"
