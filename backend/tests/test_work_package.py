"""Задание (WorkPackage) и его неизменяемые версии (FR-003, TT-09, ADR-020).

- неполное задание остаётся черновиком: выпуск требует цель, результат,
  специализацию и хотя бы один критерий;
- выпущенная версия неизменна, у неё digest; правка черновика не меняет её;
- экспорт для консоли — закреплённая копия с ID, версией и digest (JSON/YAML).
"""
import hashlib
import json
import uuid

import yaml
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.main import app
from app.models.project import ProjectMember, ProjectMemberRole
from app.models.user import User
from app.schemas.project import ProjectCreate
from app.services import project_service

FULL = {
    "goal": "Перенести расчёт метрик в отдельный сервис",
    "expected_result": "Сервис metrics с API /v1/metrics, покрытый тестами",
    "criteria": [
        {"text": "Все метрики из старого модуля считаются сервисом"},
        {"text": "Время ответа p95 < 200 мс", "required": False},
    ],
    "inputs": [{"kind": "repo", "ref": "git@github.com:org/metrics.git", "version": "main"}],
    "constraints": ["Без изменения схемы БД"],
    "specialization": "backend",
}


async def _task(client: AsyncClient, db_session: AsyncSession, owner: User) -> dict:
    p = await project_service.create_project(
        db_session, ProjectCreate(name="WP", key=uuid.uuid4().hex[:8].upper()), owner
    )
    r = await client.post(f"/api/v1/projects/{p.id}/tasks", json={"title": "Metrics"})
    return {"project_id": p.id, **r.json()}


async def test_draft_then_issue(client: AsyncClient, db_session: AsyncSession, stub_user: User):
    task = await _task(client, db_session, stub_user)
    url = f"/api/v1/tasks/{task['id']}/work-package"

    r = await client.get(url)
    assert r.status_code == 200 and r.json()["state"] == "none"

    r = await client.put(f"{url}/draft", json=FULL)
    assert r.status_code == 200 and r.json()["state"] == "draft"

    r = await client.post(f"{url}/issue")
    assert r.status_code == 201
    wp = r.json()
    assert wp["version"] == 1
    assert [c["key"] for c in wp["content"]["criteria"]] == ["c1", "c2"]
    expected = hashlib.sha256(
        json.dumps(wp["content"], sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()
    ).hexdigest()
    assert wp["digest"] == expected

    t = (await client.get(f"/api/v1/tasks/{task['id']}")).json()
    assert t["work_package_version"] == 1
    assert (await client.get(url)).json()["state"] == "issued"


async def test_incomplete_draft_cannot_be_issued(client: AsyncClient, db_session: AsyncSession, stub_user: User):
    task = await _task(client, db_session, stub_user)
    url = f"/api/v1/tasks/{task['id']}/work-package"
    await client.put(f"{url}/draft", json={"goal": "Что-то сделать", "criteria": []})

    r = await client.post(f"{url}/issue")
    assert r.status_code == 422
    detail = r.json()["detail"]
    assert detail["code"] == "WORK_PACKAGE_INCOMPLETE"
    assert set(detail["missing"]) == {"expected_result", "criteria", "specialization"}
    assert (await client.get(url)).json()["state"] == "draft"


async def test_issued_version_is_immutable(client: AsyncClient, db_session: AsyncSession, stub_user: User):
    task = await _task(client, db_session, stub_user)
    url = f"/api/v1/tasks/{task['id']}/work-package"
    await client.put(f"{url}/draft", json=FULL)
    v1 = (await client.post(f"{url}/issue")).json()

    changed = {**FULL, "goal": "Другая цель"}
    await client.put(f"{url}/draft", json=changed)
    assert (await client.get(url)).json()["state"] == "draft_changed"

    r = await client.get(f"/api/v1/work-packages/{v1['id']}")
    assert r.json()["content"]["goal"] == FULL["goal"] and r.json()["digest"] == v1["digest"]

    v2 = (await client.post(f"{url}/issue")).json()
    assert v2["version"] == 2 and v2["digest"] != v1["digest"]
    versions = (await client.get(f"/api/v1/tasks/{task['id']}/work-packages")).json()
    assert [v["version"] for v in versions] == [1, 2]


async def test_reissue_unchanged_rejected(client: AsyncClient, db_session: AsyncSession, stub_user: User):
    task = await _task(client, db_session, stub_user)
    url = f"/api/v1/tasks/{task['id']}/work-package"
    await client.put(f"{url}/draft", json=FULL)
    await client.post(f"{url}/issue")
    r = await client.post(f"{url}/issue")
    assert r.status_code == 409
    assert r.json()["detail"]["code"] == "WORK_PACKAGE_UNCHANGED"


async def test_duplicate_criterion_keys_rejected(client: AsyncClient, db_session: AsyncSession, stub_user: User):
    task = await _task(client, db_session, stub_user)
    body = {**FULL, "criteria": [{"key": "a", "text": "x"}, {"key": "a", "text": "y"}]}
    r = await client.put(f"/api/v1/tasks/{task['id']}/work-package/draft", json=body)
    assert r.status_code == 422


async def test_export_json_and_yaml(client: AsyncClient, db_session: AsyncSession, stub_user: User):
    task = await _task(client, db_session, stub_user)
    url = f"/api/v1/tasks/{task['id']}/work-package"
    await client.put(f"{url}/draft", json=FULL)
    wp = (await client.post(f"{url}/issue")).json()

    j = (await client.get(f"/api/v1/work-packages/{wp['id']}/export")).json()
    assert j["id"] == wp["id"] and j["version"] == 1 and j["digest"] == wp["digest"]
    assert j["task"]["key"] == task["key"]

    r = await client.get(f"/api/v1/work-packages/{wp['id']}/export", params={"format": "yaml"})
    assert r.headers["content-type"].startswith("application/yaml")
    y = yaml.safe_load(r.text)
    assert y["digest"] == wp["digest"] and y["content"]["goal"] == FULL["goal"]


async def test_only_manager_or_reporter_edits_package(
    client: AsyncClient, db_session: AsyncSession, stub_user: User
):
    task = await _task(client, db_session, stub_user)
    member = User(id=uuid.uuid4(), email=f"m_{uuid.uuid4().hex[:6]}@t.com", display_name="M",
                  keycloak_id=str(uuid.uuid4()), is_active=True)
    db_session.add(member)
    await db_session.flush()
    db_session.add(ProjectMember(project_id=task["project_id"], user_id=member.id, role=ProjectMemberRole.member))
    await db_session.flush()

    app.dependency_overrides[get_current_user] = lambda: member
    r = await client.put(f"/api/v1/tasks/{task['id']}/work-package/draft", json=FULL)
    assert r.status_code == 403
    assert (await client.get(f"/api/v1/tasks/{task['id']}/work-package")).status_code == 200


async def test_issue_is_audited(client: AsyncClient, db_session: AsyncSession, stub_user: User):
    task = await _task(client, db_session, stub_user)
    url = f"/api/v1/tasks/{task['id']}/work-package"
    await client.put(f"{url}/draft", json=FULL)
    wp = (await client.post(f"{url}/issue")).json()
    history = (await client.get(f"/api/v1/tasks/{task['id']}/history")).json()["items"]
    issued = [e for e in history if e["entity_type"] == "work_package"]
    assert issued and issued[-1]["action"] == "issued"
    assert issued[-1]["after"] == {"version": 1, "digest": wp["digest"]}
