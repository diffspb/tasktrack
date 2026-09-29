"""Сессии исполнения (FR-003, TT-12, ADR-022).

- исполнитель атомарно закрепляет задачу за конкретной сессией; второй процесс,
  даже под той же учётной записью, активную сессию не получает;
- контрольные точки сохраняются; сессия заканчивается только явно —
  завершением или освобождением с причиной; истечения времени нет;
- изменения с заголовком X-Task-Session относятся к действующей сессии и
  версии задания (журнал, предложение результата).
"""
import asyncio
import uuid
from datetime import UTC, datetime, timedelta

import pytest_asyncio
from fastapi import HTTPException
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.api.deps import get_current_user
from app.main import app
from app.models.project import ProjectMember, ProjectMemberRole
from app.models.session import TaskSession
from app.models.task_type import TaskType
from app.models.user import User
from app.schemas.project import ProjectCreate
from app.schemas.session import SessionCreate
from app.schemas.task import TaskCreate
from app.services import project_service, session_service, task_service

PACKAGE = {"goal": "g", "expected_result": "r", "criteria": [{"text": "c"}], "specialization": "backend"}


def act_as(user: User) -> None:
    app.dependency_overrides[get_current_user] = lambda: user


async def _user(session: AsyncSession) -> User:
    u = User(id=uuid.uuid4(), email=f"s_{uuid.uuid4().hex[:8]}@t.com", display_name="S",
             keycloak_id=str(uuid.uuid4()), is_active=True)
    session.add(u)
    await session.flush()
    return u


@pytest_asyncio.fixture
async def world(client: AsyncClient, db_session: AsyncSession, stub_user: User) -> dict:
    project = await project_service.create_project(
        db_session, ProjectCreate(name="Ses", key=uuid.uuid4().hex[:8].upper()), stub_user
    )
    worker, member = await _user(db_session), await _user(db_session)
    db_session.add_all([
        ProjectMember(project_id=project.id, user_id=worker.id, role=ProjectMemberRole.member),
        ProjectMember(project_id=project.id, user_id=member.id, role=ProjectMemberRole.member),
    ])
    await db_session.flush()
    task = (await client.post(f"/api/v1/projects/{project.id}/tasks", json={
        "title": "Run", "assignee_id": str(worker.id),
    })).json()
    await client.put(f"/api/v1/tasks/{task['id']}/work-package/draft", json=PACKAGE)
    package = (await client.post(f"/api/v1/tasks/{task['id']}/work-package/issue")).json()
    return {"project": project, "task": task, "package": package,
            "worker": worker, "member": member, "manager": stub_user}


async def _claim(client, world, **body):
    act_as(world["worker"])
    return await client.post(f"/api/v1/tasks/{world['task']['id']}/sessions",
                             json={"machine": "gpu-1", "workdir": "/work/run", "client": "claude-code", **body})


async def test_claim_pins_package_version(client, world):
    r = await _claim(client, world)
    assert r.status_code == 201, r.text
    s = r.json()
    assert s["state"] == "active" and s["role"] == "executor"
    assert s["work_package_id"] == world["package"]["id"]
    assert s["machine"] == "gpu-1" and s["user_id"] == str(world["worker"].id)


async def test_second_process_same_account_rejected(client, world):
    first = (await _claim(client, world)).json()
    r = await _claim(client, world, machine="laptop")
    assert r.status_code == 409
    detail = r.json()["detail"]
    assert detail["code"] == "SESSION_ACTIVE" and detail["session_id"] == first["id"]


async def test_only_assignee_claims_execution(client, world):
    act_as(world["member"])
    r = await client.post(f"/api/v1/tasks/{world['task']['id']}/sessions", json={})
    assert r.status_code == 403
    assert r.json()["detail"]["code"] == "NOT_ASSIGNEE"


async def test_checkpoints_and_complete(client, world):
    s = (await _claim(client, world)).json()
    r = await client.post(f"/api/v1/sessions/{s['id']}/checkpoints",
                          json={"note": "данные загружены", "data": {"step": 1}})
    assert r.status_code == 201
    got = (await client.get(f"/api/v1/sessions/{s['id']}")).json()
    assert got["last_checkpoint_at"] is not None
    assert [c["note"] for c in got["checkpoints"]] == ["данные загружены"]

    act_as(world["member"])
    r = await client.post(f"/api/v1/sessions/{s['id']}/checkpoints", json={"note": "чужая"})
    assert r.status_code == 403

    act_as(world["worker"])
    r = await client.post(f"/api/v1/sessions/{s['id']}/complete", json={"result": "готово"})
    assert r.status_code == 200 and r.json()["state"] == "completed"
    assert (await _claim(client, world)).status_code == 201


async def test_no_expiry_release_needs_explicit_reason(client, db_session, world):
    s = (await _claim(client, world)).json()
    row = await db_session.get(TaskSession, uuid.UUID(s["id"]))
    row.last_checkpoint_at = datetime.now(UTC) - timedelta(days=3)
    await db_session.flush()
    assert (await _claim(client, world)).status_code == 409  # давность — не подтверждение остановки

    act_as(world["member"])
    r = await client.post(f"/api/v1/sessions/{s['id']}/release", json={"reason": "кажется, завис"})
    assert r.status_code == 403

    act_as(world["manager"])
    r = await client.post(f"/api/v1/sessions/{s['id']}/release", json={"reason": " "})
    assert r.status_code == 422
    r = await client.post(f"/api/v1/sessions/{s['id']}/release",
                          json={"reason": "процесс на gpu-1 проверен и остановлен"})
    assert r.status_code == 200
    assert r.json()["state"] == "released" and r.json()["ended_by"] == str(world["manager"].id)
    assert (await _claim(client, world)).status_code == 201


async def test_session_header_binds_changes(client, world):
    s = (await _claim(client, world)).json()
    headers = {"X-Task-Session": s["id"]}
    tid = world["task"]["id"]

    r = await client.post(f"/api/v1/tasks/{tid}/proposals", json={"summary": "готово"}, headers=headers)
    assert r.status_code == 201
    assert r.json()["session_id"] == s["id"]
    assert r.json()["provenance"]["session"]["machine"] == "gpu-1"

    await client.post(f"/api/v1/tasks/{tid}/comments", json={"content": "прогресс"}, headers=headers)
    history = (await client.get(f"/api/v1/tasks/{tid}/history")).json()["items"]
    comment_event = next(e for e in history if e["entity_type"] == "comment")
    assert comment_event["session_id"] == s["id"]


async def test_session_header_must_be_own_active_session(client, world):
    s = (await _claim(client, world)).json()
    tid = world["task"]["id"]

    act_as(world["member"])
    r = await client.post(f"/api/v1/tasks/{tid}/comments", json={"content": "x"},
                          headers={"X-Task-Session": s["id"]})
    assert r.status_code == 409
    assert r.json()["detail"]["code"] == "SESSION_NOT_ACTIVE"

    act_as(world["worker"])
    await client.post(f"/api/v1/sessions/{s['id']}/complete", json={})
    r = await client.post(f"/api/v1/tasks/{tid}/comments", json={"content": "x"},
                          headers={"X-Task-Session": s["id"]})
    assert r.status_code == 409
    r = await client.post(f"/api/v1/tasks/{tid}/comments", json={"content": "x"},
                          headers={"X-Task-Session": "not-a-uuid"})
    assert r.status_code == 400


# ── Гонка двух процессов (реальные транзакции) ──────────────────────────────

@pytest_asyncio.fixture(scope="module")
async def committed(make_database, alembic):
    url = await make_database()
    await alembic(url, "upgrade", "head")
    engine = create_async_engine(url)
    Session = async_sessionmaker(engine, expire_on_commit=False)
    async with Session() as s:
        s.add(TaskType(key="task", name="Задача", is_system=True))
        user = User(id=uuid.uuid4(), email="race@t.com", display_name="R",
                    keycloak_id=str(uuid.uuid4()), is_active=True)
        s.add(user)
        await s.flush()
        project = await project_service.create_project(s, ProjectCreate(name="R", key="SESRACE"), user)
        task = await task_service.create_task(s, project.id, TaskCreate(title="T", assignee_id=user.id), user)
    yield Session, user, task.id
    await engine.dispose()


async def test_parallel_claims_one_wins(committed):
    Session, user, task_id = committed

    async def claim(i):
        async with Session() as s:
            return await session_service.claim(s, task_id, SessionCreate(machine=f"m{i}"), user)

    results = await asyncio.gather(*(claim(i) for i in range(3)), return_exceptions=True)
    won = [r for r in results if isinstance(r, TaskSession)]
    lost = [r for r in results if isinstance(r, HTTPException)]
    assert len(won) == 1 and len(lost) == 2, results
    assert all(e.status_code == 409 for e in lost)
    async with Session() as s:
        active = (await s.scalars(select(TaskSession).where(
            TaskSession.task_id == task_id, TaskSession.state == "active",
        ))).all()
        assert len(active) == 1
