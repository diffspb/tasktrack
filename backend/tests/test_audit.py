"""Сохраняемый аудит и журнал событий (FR-003, TT-06, ADR-018).

- событие пишется в той же транзакции, что и изменение: неудачная команда
  события не оставляет;
- событие хранит автора, причину и состояние до/после;
- чтение по курсору без пропусков, даже когда транзакции фиксируются не в том
  порядке, в каком начали писать; повтор чтения с тем же курсором безопасен.
"""
import uuid
from urllib.parse import quote

import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.api.deps import get_current_user
from app.main import app
from app.models.audit import AuditEvent
from app.models.project import ProjectMember, ProjectMemberRole, ProjectVisibility
from app.models.user import User
from app.models.workflow import Status, Workflow
from app.schemas.project import ProjectCreate
from app.services import audit_service, project_service


async def _make_user(session: AsyncSession, **kw) -> User:
    u = User(id=uuid.uuid4(), email=f"a_{uuid.uuid4().hex[:8]}@t.com", display_name="A",
             keycloak_id=str(uuid.uuid4()), is_active=True, **kw)
    session.add(u)
    await session.flush()
    return u


async def _project(session: AsyncSession, owner: User, **kw) -> uuid.UUID:
    p = await project_service.create_project(
        session, ProjectCreate(name="Audit", key=uuid.uuid4().hex[:8].upper(), **kw), owner
    )
    return p.id


async def _log(client: AsyncClient, project_id, **params) -> dict:
    r = await client.get(f"/api/v1/projects/{project_id}/audit-log", params=params)
    assert r.status_code == 200, r.text
    return r.json()


# ── Что записывается ────────────────────────────────────────────────────────

async def test_task_lifecycle_is_recorded(
    client: AsyncClient, db_session: AsyncSession, stub_user: User
):
    pid = await _project(db_session, stub_user)
    r = await client.post(f"/api/v1/projects/{pid}/tasks", json={
        "title": "Audit me", "assignee_id": str(stub_user.id),
    })
    task = r.json()

    r = await client.patch(
        f"/api/v1/tasks/{task['id']}", json={"title": "Audited", "version": 1},
        headers={"X-Change-Reason": quote("уточнено название")},
    )
    assert r.status_code == 200

    wf = await db_session.scalar(select(Workflow).where(Workflow.project_id == pid))
    inprog = await db_session.scalar(
        select(Status).where(Status.workflow_id == wf.id, Status.name == "In Progress")
    )
    await client.post(f"/api/v1/tasks/{task['id']}/transition", json={"status_id": str(inprog.id)})
    await client.delete(f"/api/v1/tasks/{task['id']}")

    items = (await _log(client, pid))["items"]
    task_events = [e for e in items if e["entity_type"] == "task"]
    assert [e["action"] for e in task_events] == ["created", "updated", "status_changed", "deleted"]
    created, updated, moved, deleted = task_events

    assert created["actor_id"] == str(stub_user.id)
    assert created["after"]["title"] == "Audit me" and created["before"] is None
    assert updated["before"] == {"title": "Audit me", "version": 1}
    assert updated["after"] == {"title": "Audited", "version": 2}
    assert updated["reason"] == "уточнено название"
    assert moved["before"]["current_status_id"] == task["current_status_id"]
    assert moved["after"]["current_status_id"] == str(inprog.id)
    assert deleted["before"]["title"] == "Audited" and deleted["after"] is None
    assert all(e["task_id"] == task["id"] for e in task_events)


async def test_comments_links_and_task_history(
    client: AsyncClient, db_session: AsyncSession, stub_user: User
):
    from app.models.link_type import LinkType

    pid = await _project(db_session, stub_user)
    a = (await client.post(f"/api/v1/projects/{pid}/tasks", json={"title": "A"})).json()
    b = (await client.post(f"/api/v1/projects/{pid}/tasks", json={"title": "B"})).json()
    lt = LinkType(name=f"lt-{uuid.uuid4().hex[:6]}", outward_name="blocks", inward_name="is blocked by")
    db_session.add(lt)
    await db_session.flush()

    c = (await client.post(f"/api/v1/tasks/{a['id']}/comments", json={"content": "first"})).json()
    await client.patch(f"/api/v1/comments/{c['id']}", json={"content": "second"})
    link = (await client.post(f"/api/v1/tasks/{a['id']}/links", json={
        "target_task_id": b["id"], "link_type_id": str(lt.id),
    })).json()
    await client.delete(f"/api/v1/tasks/{a['id']}/links/{link['id']}")
    await client.delete(f"/api/v1/comments/{c['id']}")

    r = await client.get(f"/api/v1/tasks/{a['id']}/history")
    assert r.status_code == 200
    history = [(e["entity_type"], e["action"]) for e in r.json()["items"]]
    assert history == [
        ("task", "created"),
        ("comment", "created"), ("comment", "updated"),
        ("task_link", "created"), ("task_link", "deleted"),
        ("comment", "deleted"),
    ]
    updated = r.json()["items"][2]
    assert updated["before"] == {"content": "first"} and updated["after"] == {"content": "second"}


async def test_membership_changes_are_recorded(
    client: AsyncClient, db_session: AsyncSession, stub_user: User
):
    pid = await _project(db_session, stub_user)
    other = await _make_user(db_session)
    r = await client.post(f"/api/v1/projects/{pid}/members", json={
        "user_id": str(other.id), "role": "viewer",
    })
    assert r.status_code in (200, 201), r.text
    r = await client.delete(f"/api/v1/projects/{pid}/members/{other.id}")
    assert r.status_code in (200, 204), r.text

    items = (await _log(client, pid))["items"]
    assert (items[0]["entity_type"], items[0]["action"]) == ("project", "created")
    assert items[0]["after"]["owner_id"] == str(stub_user.id)
    events = [e for e in items if e["entity_type"] == "project_member"]
    assert [e["action"] for e in events] == ["created", "deleted"]
    assert events[0]["after"] == {"user_id": str(other.id), "role": "viewer"}
    assert events[1]["before"] == {"user_id": str(other.id), "role": "viewer"}


async def test_failed_command_leaves_no_event(
    client: AsyncClient, db_session: AsyncSession, stub_user: User
):
    pid = await _project(db_session, stub_user)
    task = (await client.post(f"/api/v1/projects/{pid}/tasks", json={"title": "T"})).json()
    before = len((await _log(client, pid))["items"])

    r = await client.patch(f"/api/v1/tasks/{task['id']}", json={"title": "X", "version": 99})
    assert r.status_code == 409
    assert len((await _log(client, pid))["items"]) == before


# ── Чтение по курсору и доступ ──────────────────────────────────────────────

async def test_cursor_pagination_is_complete_and_repeatable(
    client: AsyncClient, db_session: AsyncSession, stub_user: User
):
    pid = await _project(db_session, stub_user)
    for i in range(5):
        await client.post(f"/api/v1/projects/{pid}/tasks", json={"title": f"t{i}"})

    everything = [e["id"] for e in (await _log(client, pid))["items"]]
    page1 = await _log(client, pid, limit=2)
    page2 = await _log(client, pid, limit=2, after=page1["next_cursor"])
    page2_again = await _log(client, pid, limit=2, after=page1["next_cursor"])
    rest = await _log(client, pid, after=page2["next_cursor"])

    got = [e["id"] for e in page1["items"] + page2["items"] + rest["items"]]
    assert got == everything and len(everything) == len(set(everything))
    assert page2 == page2_again
    tail = await _log(client, pid, after=rest["next_cursor"])
    assert tail["items"] == [] and tail["next_cursor"] == rest["next_cursor"]


async def test_audit_log_access(client: AsyncClient, db_session: AsyncSession, stub_user: User):
    pid = await _project(db_session, stub_user, visibility=ProjectVisibility.restricted)
    viewer = await _make_user(db_session)
    outsider = await _make_user(db_session)
    db_session.add(ProjectMember(project_id=pid, user_id=viewer.id, role=ProjectMemberRole.viewer))
    await db_session.flush()

    app.dependency_overrides[get_current_user] = lambda: viewer
    assert (await client.get(f"/api/v1/projects/{pid}/audit-log")).status_code == 200
    app.dependency_overrides[get_current_user] = lambda: outsider
    assert (await client.get(f"/api/v1/projects/{pid}/audit-log")).status_code == 404


async def test_invalid_cursor_rejected(client: AsyncClient, db_session: AsyncSession, stub_user: User):
    pid = await _project(db_session, stub_user)
    r = await client.get(f"/api/v1/projects/{pid}/audit-log", params={"after": "garbage"})
    assert r.status_code == 400
    assert r.json()["detail"]["code"] == "INVALID_CURSOR"


async def test_security_events_only_for_superuser(
    client: AsyncClient, db_session: AsyncSession, stub_user: User
):
    root = await _make_user(db_session, is_superuser=True)
    app.dependency_overrides[get_current_user] = lambda: root
    sa = (await client.post("/api/v1/admin/service-accounts", json={
        "email": f"sa_{uuid.uuid4().hex[:6]}@agents", "display_name": "SA",
    })).json()
    key = (await client.post(f"/api/v1/admin/service-accounts/{sa['id']}/api-keys", json={"name": "k"})).json()
    await client.delete(f"/api/v1/admin/api-keys/{key['id']}")

    r = await client.get("/api/v1/admin/audit-log")
    assert r.status_code == 200
    events = [(e["entity_type"], e["action"]) for e in r.json()["items"]]
    assert ("service_account", "created") in events
    assert ("api_key", "created") in events and ("api_key", "revoked") in events
    assert all("token" not in (e["after"] or {}) for e in r.json()["items"])
    assert all(e["actor_id"] == str(root.id) for e in r.json()["items"])

    app.dependency_overrides[get_current_user] = lambda: stub_user
    assert (await client.get("/api/v1/admin/audit-log")).status_code == 403


# ── Без пропусков при конкурентной фиксации (реальные транзакции) ────────────

@pytest_asyncio.fixture(scope="module")
async def committed_engine(make_database, alembic):
    url = await make_database()
    await alembic(url, "upgrade", "head")
    engine = create_async_engine(url)
    yield engine
    await engine.dispose()


async def test_no_gap_when_commits_are_out_of_order(committed_engine):
    """T1 пишет первым, но фиксируется последним. Читатель не должен
    сдвинуть курсор за событие T2 раньше, чем станет видно событие T1."""
    Session = async_sessionmaker(committed_engine, expire_on_commit=False)
    project_id = uuid.uuid4()

    async def record(session, label):
        await audit_service.record(
            session, actor_id=None, project_id=project_id,
            entity_type="task", entity_id=uuid.uuid4(), action=label,
        )
        await session.flush()

    async with Session() as t1, Session() as t2, Session() as reader:
        await record(t1, "first")            # T1 получил xid раньше
        await record(t2, "second")
        await t2.commit()                    # ...но T2 зафиксирован раньше

        page = await audit_service.list_events(reader, project_id=project_id)
        await reader.commit()
        assert page.items == []              # T2 не отдаётся, пока T1 в полёте

        await t1.commit()
        page = await audit_service.list_events(reader, project_id=project_id)
        await reader.commit()
        assert [e.action for e in page.items] == ["first", "second"]

        again = await audit_service.list_events(reader, project_id=project_id, after=page.next_cursor)
        assert again.items == []

    async with Session() as s:
        stored = (await s.scalars(select(AuditEvent).where(AuditEvent.project_id == project_id))).all()
        assert len(stored) == 2


async def test_configuration_changes_are_recorded(
    client: AsyncClient, db_session: AsyncSession, stub_user: User
):
    pid = await _project(db_session, stub_user)
    wf = (await client.post(f"/api/v1/projects/{pid}/workflows", json={"name": "Extra"})).json()
    st = (await client.post(f"/api/v1/workflows/{wf['id']}/statuses", json={
        "name": "Queued", "category": "initial", "is_default": True, "position": 0,
    })).json()
    await client.patch(f"/api/v1/statuses/{st['id']}", json={"name": "Queue"})
    await client.delete(f"/api/v1/statuses/{st['id']}")

    events = [(e["entity_type"], e["action"]) for e in (await _log(client, pid))["items"]]
    assert ("workflow", "created") in events
    assert ("status", "created") in events and ("status", "updated") in events
    assert ("status", "deleted") in events


async def test_import_is_recorded(client: AsyncClient, db_session: AsyncSession, stub_user: User):
    from app.services import project_export_service

    pid = await _project(db_session, stub_user)
    await client.post(f"/api/v1/projects/{pid}/tasks", json={"title": "Экспортируемая"})
    data = await project_export_service.export_project(db_session, pid, stub_user)
    stub_user.is_superuser = True
    r = await client.post("/api/v1/projects/import", json={"data": data, "new_key": uuid.uuid4().hex[:8].upper()})
    assert r.status_code == 201, r.text
    events = [(e["entity_type"], e["action"]) for e in (await _log(client, r.json()["id"]))["items"]]
    assert ("project", "imported") in events and ("task", "created") in events
