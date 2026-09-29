"""Представление руководителя (FR-003, TT-22): необеспеченная работа, очередь
проверки, причины ожидания, зависшие сессии, разрез по специализации."""
import uuid
from datetime import UTC, datetime, timedelta

from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.main import app
from app.models.link_type import LinkType
from app.models.project import ProjectMember, ProjectMemberRole
from app.models.session import TaskSession
from app.models.user import User
from app.schemas.project import ProjectCreate
from app.services import project_service


def pkg(spec: str) -> dict:
    return {"goal": "g", "expected_result": "r", "criteria": [{"text": "c"}], "specialization": spec}


async def test_control_overview(client: AsyncClient, db_session: AsyncSession, stub_user: User):
    project = await project_service.create_project(
        db_session, ProjectCreate(name="Ctl", key=uuid.uuid4().hex[:8].upper()), stub_user
    )
    worker = User(id=uuid.uuid4(), email=f"w_{uuid.uuid4().hex[:6]}@t.com", display_name="W",
                  keycloak_id=str(uuid.uuid4()), is_active=True)
    db_session.add(worker)
    await db_session.flush()
    db_session.add(ProjectMember(project_id=project.id, user_id=worker.id, role=ProjectMemberRole.member))
    await db_session.flush()
    await client.patch(f"/api/v1/projects/{project.id}/members/{stub_user.id}", json={"is_reviewer": True})
    base = f"/api/v1/projects/{project.id}/tasks"

    async def task(title, **kw):
        return (await client.post(base, json={"title": title, **kw})).json()

    async def issue(t, spec):
        await client.put(f"/api/v1/tasks/{t['id']}/work-package/draft", json=pkg(spec))
        await client.post(f"/api/v1/tasks/{t['id']}/work-package/issue")

    bare = await task("Без задания", assignee_id=str(worker.id))
    no_one = await task("Без исполнителя")
    await issue(no_one, "backend")
    review = await task("На проверке", assignee_id=str(worker.id))
    await issue(review, "backend")
    changed = await task("Задание изменено", assignee_id=str(worker.id))
    await issue(changed, "frontend")
    await client.put(f"/api/v1/tasks/{changed['id']}/work-package/draft", json={**pkg("frontend"), "goal": "другая"})
    stale = await task("Зависшая сессия", assignee_id=str(worker.id))
    await issue(stale, "backend")
    blocked = await task("Заблокирована", assignee_id=str(worker.id))
    await issue(blocked, "backend")

    lt = LinkType(name=f"blk-{uuid.uuid4().hex[:6]}", outward_name="blocks", inward_name="is blocked by",
                  constraint={"type": "blocking"})
    db_session.add(lt)
    await db_session.flush()
    await client.post(f"/api/v1/tasks/{bare['id']}/links", json={
        "target_task_id": blocked["id"], "link_type_id": str(lt.id),
    })

    app.dependency_overrides[get_current_user] = lambda: worker
    await client.post(f"/api/v1/tasks/{review['id']}/proposals", json={"summary": "готово"})
    s = (await client.post(f"/api/v1/tasks/{stale['id']}/sessions", json={"machine": "gpu-1"})).json()
    row = await db_session.get(TaskSession, uuid.UUID(s["id"]))
    row.created_at = datetime.now(UTC) - timedelta(hours=30)
    await db_session.flush()
    app.dependency_overrides[get_current_user] = lambda: stub_user

    r = await client.get(f"/api/v1/projects/{project.id}/control")
    assert r.status_code == 200, r.text
    data = r.json()
    by_key = {i["key"]: i for i in data["items"]}

    assert "no_work_package" in by_key[bare["key"]]["waiting"]
    assert "no_assignee" in by_key[no_one["key"]]["waiting"]
    assert by_key[review["key"]]["waiting"] == ["awaiting_review"]
    assert "work_package_changed" in by_key[changed["key"]]["waiting"]
    assert "session_stale" in by_key[stale["key"]]["waiting"]
    assert by_key[stale["key"]]["active_session"]["machine"] == "gpu-1"
    assert by_key[blocked["key"]]["waiting"] == ["blocked"]
    assert by_key[blocked["key"]]["blocked_by"] == [bare["key"]]

    summary = data["summary"]
    assert summary["by_reason"]["awaiting_review"] == 1
    assert summary["by_specialization"]["backend"] == 4
    assert summary["by_specialization"]["frontend"] == 1

    r = await client.get(f"/api/v1/projects/{project.id}/control", params={"reason": "awaiting_review"})
    assert [i["key"] for i in r.json()["items"]] == [review["key"]]
    r = await client.get(f"/api/v1/projects/{project.id}/control", params={"specialization": "frontend"})
    assert [i["key"] for i in r.json()["items"]] == [changed["key"]]


async def test_control_requires_project_access(client: AsyncClient, db_session: AsyncSession, stub_user: User):
    project = await project_service.create_project(
        db_session, ProjectCreate(name="Ctl2", key=uuid.uuid4().hex[:8].upper()), stub_user
    )
    outsider = User(id=uuid.uuid4(), email=f"o_{uuid.uuid4().hex[:6]}@t.com", display_name="O",
                    keycloak_id=str(uuid.uuid4()), is_active=True)
    db_session.add(outsider)
    await db_session.flush()
    app.dependency_overrides[get_current_user] = lambda: outsider
    assert (await client.get(f"/api/v1/projects/{project.id}/control")).status_code == 404
