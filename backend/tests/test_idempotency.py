"""Безопасный повтор команд по Idempotency-Key (FR-003, TT-04, ADR-019).

- повтор после потерянного ответа возвращает прежний результат, команда не выполняется дважды;
- другой запрос с тем же ключом отклонён;
- право доступа проверяется и при повторе;
- одновременные дубли выполняют команду один раз.
"""
import asyncio
import uuid
from datetime import UTC, datetime, timedelta

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.api.deps import get_current_user, get_session
from app.main import app
from app.models.idempotency import IdempotencyKey
from app.models.project import ProjectMember, ProjectMemberRole
from app.models.task import Task
from app.models.task_type import TaskType
from app.models.user import User
from app.schemas.project import ProjectCreate
from app.services import project_service


def _key() -> dict:
    return {"Idempotency-Key": uuid.uuid4().hex}


async def _project(session: AsyncSession, owner: User) -> uuid.UUID:
    p = await project_service.create_project(
        session, ProjectCreate(name="Idem", key=uuid.uuid4().hex[:8].upper()), owner
    )
    return p.id


async def _count_tasks(session: AsyncSession, project_id) -> int:
    return await session.scalar(
        select(func.count()).select_from(Task).where(Task.project_id == project_id)
    )


async def test_retry_returns_same_result(client: AsyncClient, db_session: AsyncSession, stub_user: User):
    pid = await _project(db_session, stub_user)
    headers = _key()
    first = await client.post(f"/api/v1/projects/{pid}/tasks", json={"title": "Once"}, headers=headers)
    again = await client.post(f"/api/v1/projects/{pid}/tasks", json={"title": "Once"}, headers=headers)

    assert first.status_code == again.status_code == 201
    assert again.json() == first.json()
    assert again.headers.get("idempotent-replayed") == "true"
    assert "idempotent-replayed" not in first.headers
    assert await _count_tasks(db_session, pid) == 1


async def test_without_key_nothing_changes(client: AsyncClient, db_session: AsyncSession, stub_user: User):
    pid = await _project(db_session, stub_user)
    await client.post(f"/api/v1/projects/{pid}/tasks", json={"title": "A"})
    await client.post(f"/api/v1/projects/{pid}/tasks", json={"title": "A"})
    assert await _count_tasks(db_session, pid) == 2


async def test_same_key_other_request_rejected(client: AsyncClient, db_session: AsyncSession, stub_user: User):
    pid = await _project(db_session, stub_user)
    headers = _key()
    await client.post(f"/api/v1/projects/{pid}/tasks", json={"title": "A"}, headers=headers)
    r = await client.post(f"/api/v1/projects/{pid}/tasks", json={"title": "B"}, headers=headers)
    assert r.status_code == 422
    assert r.json()["detail"]["code"] == "IDEMPOTENCY_KEY_REUSED"
    assert await _count_tasks(db_session, pid) == 1


async def test_keys_are_scoped_per_user(client: AsyncClient, db_session: AsyncSession, stub_user: User):
    pid = await _project(db_session, stub_user)
    other = User(id=uuid.uuid4(), email=f"o_{uuid.uuid4().hex[:6]}@t.com", display_name="O",
                 keycloak_id=str(uuid.uuid4()), is_active=True)
    db_session.add(other)
    await db_session.flush()
    db_session.add(ProjectMember(project_id=pid, user_id=other.id, role=ProjectMemberRole.member))
    await db_session.flush()
    headers = _key()

    await client.post(f"/api/v1/projects/{pid}/tasks", json={"title": "A"}, headers=headers)
    app.dependency_overrides[get_current_user] = lambda: other
    r = await client.post(f"/api/v1/projects/{pid}/tasks", json={"title": "A"}, headers=headers)
    assert r.status_code == 201 and "idempotent-replayed" not in r.headers
    assert await _count_tasks(db_session, pid) == 2


async def test_failed_command_is_not_remembered(client: AsyncClient, db_session: AsyncSession, stub_user: User):
    pid = await _project(db_session, stub_user)
    task = (await client.post(f"/api/v1/projects/{pid}/tasks", json={"title": "T"})).json()
    headers = _key()
    body = {"title": "X", "version": 99}

    r1 = await client.patch(f"/api/v1/tasks/{task['id']}", json=body, headers=headers)
    r2 = await client.patch(f"/api/v1/tasks/{task['id']}", json=body, headers=headers)
    assert r1.status_code == r2.status_code == 409
    assert "idempotent-replayed" not in r2.headers  # выполнено заново, а не воспроизведено

    # ключ не занят: тот же ключ с исправленным запросом проходит
    r3 = await client.patch(f"/api/v1/tasks/{task['id']}", json={"title": "X", "version": 1}, headers=headers)
    assert r3.status_code == 200


async def test_access_rechecked_on_replay(client: AsyncClient, db_session: AsyncSession, stub_user: User):
    pid = await _project(db_session, stub_user)
    member = User(id=uuid.uuid4(), email=f"m_{uuid.uuid4().hex[:6]}@t.com", display_name="M",
                  keycloak_id=str(uuid.uuid4()), is_active=True)
    db_session.add(member)
    await db_session.flush()
    membership = ProjectMember(project_id=pid, user_id=member.id, role=ProjectMemberRole.member)
    db_session.add(membership)
    await db_session.flush()
    headers = _key()

    app.dependency_overrides[get_current_user] = lambda: member
    r = await client.post(f"/api/v1/projects/{pid}/tasks", json={"title": "Mine"}, headers=headers)
    assert r.status_code == 201

    membership.role = ProjectMemberRole.viewer
    await db_session.flush()
    r = await client.post(f"/api/v1/projects/{pid}/tasks", json={"title": "Mine"}, headers=headers)
    assert r.status_code == 403
    assert "idempotent-replayed" not in r.headers


async def test_outcome_unknown_after_lost_completion(
    client: AsyncClient, db_session: AsyncSession, stub_user: User
):
    """Резерв зафиксирован вместе с командой, но ответ не сохранён (сбой процесса)."""
    pid = await _project(db_session, stub_user)
    key = uuid.uuid4().hex
    from app.services.idempotency_service import request_hash

    db_session.add(IdempotencyKey(
        user_id=stub_user.id, key=key,
        request_hash=request_hash("POST", f"/api/v1/projects/{pid}/tasks", b'{"title":"Lost"}'),
        created_at=datetime.now(UTC) - timedelta(minutes=5),
    ))
    await db_session.flush()
    r = await client.post(
        f"/api/v1/projects/{pid}/tasks", content=b'{"title":"Lost"}',
        headers={"Idempotency-Key": key, "Content-Type": "application/json"},
    )
    assert r.status_code == 409
    assert r.json()["detail"]["code"] == "IDEMPOTENCY_OUTCOME_UNKNOWN"
    assert await _count_tasks(db_session, pid) == 0


async def test_invalid_key_rejected(client: AsyncClient, db_session: AsyncSession, stub_user: User):
    pid = await _project(db_session, stub_user)
    r = await client.post(
        f"/api/v1/projects/{pid}/tasks", json={"title": "A"}, headers={"Idempotency-Key": "x" * 300}
    )
    assert r.status_code == 400
    assert r.json()["detail"]["code"] == "IDEMPOTENCY_KEY_INVALID"


# ── Одновременные дубли (реальные транзакции) ───────────────────────────────

@pytest_asyncio.fixture(scope="module")
async def committed_app(make_database, alembic):
    """App wired to a fresh migrated database: every request gets its own session."""
    url = await make_database()
    await alembic(url, "upgrade", "head")
    engine = create_async_engine(url)
    Session = async_sessionmaker(engine, expire_on_commit=False)
    async with Session() as s:
        s.add(TaskType(key="task", name="Задача", is_system=True))
        user = User(id=uuid.uuid4(), email="idem@t.com", display_name="I",
                    keycloak_id=str(uuid.uuid4()), is_active=True)
        s.add(user)
        await s.flush()
        project = await project_service.create_project(
            s, ProjectCreate(name="Race", key="IDEMRACE"), user
        )
    yield Session, user, project.id
    await engine.dispose()


async def test_concurrent_duplicates_execute_once(committed_app):
    Session, user, pid = committed_app

    async def session_per_request():
        async with Session() as s:
            yield s

    app.dependency_overrides[get_session] = session_per_request
    app.dependency_overrides[get_current_user] = lambda: user
    try:
        headers = _key()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            results = await asyncio.gather(*(
                ac.post(f"/api/v1/projects/{pid}/tasks", json={"title": "Race"}, headers=headers)
                for _ in range(3)
            ))
    finally:
        app.dependency_overrides.clear()

    assert [r.status_code for r in results] == [201, 201, 201], [r.text for r in results]
    assert len({r.json()["id"] for r in results}) == 1
    async with Session() as s:
        assert await _count_tasks(s, pid) == 1
