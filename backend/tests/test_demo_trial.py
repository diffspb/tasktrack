"""Конечное демонстрационное испытание FR-003 — в части, не зависящей от внешних систем.

Два исполнителя (агенты) берут задания своих проектов, третий участник проверяет.
Одна операция приходит повторно, один исполнитель теряет связь, одно задание
меняет редакцию, одно старое решение оказывается неприменимым (исследование),
комментарий и его правка не создают готовности. Приёмку поставки фиксирует
менеджер как полученный факт.
"""
import uuid

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.bootstrap import ensure_process_types
from app.main import app
from app.models.project import ProjectMember, ProjectMemberRole
from app.models.user import User
from app.schemas.project import ProjectCreate
from app.services import project_service


def act_as(user: User) -> None:
    app.dependency_overrides[get_current_user] = lambda: user


async def _user(s: AsyncSession, name: str, service: bool = False) -> User:
    u = User(id=uuid.uuid4(), email=f"{name}_{uuid.uuid4().hex[:6]}@t.com", display_name=name,
             keycloak_id=(f"service:{uuid.uuid4()}" if service else str(uuid.uuid4())),
             is_active=True, is_service=service)
    s.add(u)
    await s.flush()
    return u


def package(goal: str) -> dict:
    return {"goal": goal, "expected_result": "PR с изменением", "specialization": "backend",
            "criteria": [{"text": "Тесты проходят"}, {"text": "Документация обновлена", "required": False}]}


async def test_demo_trial(client: AsyncClient, db_session: AsyncSession, stub_user: User):
    await ensure_process_types(db_session)
    manager = stub_user
    agent_a, agent_b = await _user(db_session, "agent-a", True), await _user(db_session, "agent-b", True)
    reviewer = await _user(db_session, "reviewer")

    projects = []
    for key_suffix, agent in (("A", agent_a), ("B", agent_b)):
        p = await project_service.create_project(
            db_session, ProjectCreate(name=f"Proj {key_suffix}", key=f"DEMO{key_suffix}{uuid.uuid4().hex[:3].upper()}"),
            manager,
        )
        db_session.add_all([
            ProjectMember(project_id=p.id, user_id=agent.id, role=ProjectMemberRole.member),
            ProjectMember(project_id=p.id, user_id=reviewer.id, role=ProjectMemberRole.member, is_reviewer=True),
        ])
        projects.append(p)
    await db_session.flush()

    act_as(manager)
    tasks = []
    for p, agent in zip(projects, (agent_a, agent_b)):
        t = (await client.post(f"/api/v1/projects/{p.id}/tasks", json={
            "title": f"Работа {p.key}", "task_type_key": "execution", "assignee_id": str(agent.id),
        })).json()
        await client.put(f"/api/v1/tasks/{t['id']}/work-package/draft", json=package(f"Цель {p.key}"))
        assert (await client.post(f"/api/v1/tasks/{t['id']}/work-package/issue")).status_code == 201
        tasks.append(t)
    task_a, task_b = tasks

    # ── Агент A: сессия, результат; операция приходит повторно ──────────────
    act_as(agent_a)
    sa = (await client.post(f"/api/v1/tasks/{task_a['id']}/sessions", json={"machine": "gpu-a"})).json()
    await client.post(f"/api/v1/sessions/{sa['id']}/checkpoints", json={"note": "тесты зелёные"})
    body = {"summary": "Готово", "links": [{"kind": "pr", "url": "https://git/a/pull/1"}],
            "criteria": [{"key": "c1", "status": "met"}]}
    headers = {"X-Task-Session": sa["id"], "Idempotency-Key": "a-submit-1"}
    first = await client.post(f"/api/v1/tasks/{task_a['id']}/proposals", json=body, headers=headers)
    again = await client.post(f"/api/v1/tasks/{task_a['id']}/proposals", json=body, headers=headers)
    assert first.status_code == again.status_code == 201
    assert first.json()["id"] == again.json()["id"] and again.headers["idempotent-replayed"] == "true"
    assert len((await client.get(f"/api/v1/tasks/{task_a['id']}/proposals")).json()) == 1

    # ── Агент B: комментарий и его правка не создают готовности ────────────
    act_as(agent_b)
    sb = (await client.post(f"/api/v1/tasks/{task_b['id']}/sessions", json={"machine": "gpu-b"})).json()
    c = (await client.post(f"/api/v1/tasks/{task_b['id']}/comments",
                           json={"content": "всё сделано", "labels": ["solution"]})).json()
    await client.patch(f"/api/v1/comments/{c['id']}", json={"content": "всё точно сделано"})
    assert (await client.get(f"/api/v1/tasks/{task_b['id']}")).json()["result_state"] == "none"

    # ── Агент B теряет связь: перезапущенный процесс не забирает работу ────
    r = await client.post(f"/api/v1/tasks/{task_b['id']}/sessions", json={"machine": "gpu-b-restarted"})
    assert r.status_code == 409 and r.json()["detail"]["session_id"] == sb["id"]

    # ── Задание B меняет редакцию, пока идёт работа ─────────────────────────
    act_as(manager)
    await client.put(f"/api/v1/tasks/{task_b['id']}/work-package/draft", json=package("Цель B, редакция 2"))
    control = (await client.get(f"/api/v1/projects/{projects[1].id}/control")).json()
    row = next(i for i in control["items"] if i["id"] == task_b["id"])
    assert "work_package_changed" in row["waiting"]
    v2 = (await client.post(f"/api/v1/tasks/{task_b['id']}/work-package/issue")).json()
    assert v2["version"] == 2

    # процесс на gpu-b проверен и остановлен — менеджер освобождает сессию явно
    r = await client.post(f"/api/v1/sessions/{sb['id']}/release", json={"reason": "gpu-b проверен, процесс остановлен"})
    assert r.status_code == 200

    act_as(agent_b)
    sb2 = (await client.post(f"/api/v1/tasks/{task_b['id']}/sessions", json={"machine": "gpu-b-restarted"})).json()
    assert sb2["work_package_id"] == v2["id"]  # новая сессия работает по новой редакции
    pb = (await client.post(f"/api/v1/tasks/{task_b['id']}/proposals", json={
        "summary": "Готово по редакции 2", "criteria": [{"key": "c1", "status": "met"}],
    }, headers={"X-Task-Session": sb2["id"]})).json()
    assert pb["work_package_id"] == v2["id"]

    # ── Без проверки задача не закрывается ───────────────────────────────────
    wf_a = (await client.get(f"/api/v1/workflows/{task_a['workflow_id']}")).json()
    by_name = {s["name"]: s["id"] for s in wf_a["statuses"]}
    act_as(agent_a)
    for step in ("In Progress", "On Review"):
        assert (await client.post(f"/api/v1/tasks/{task_a['id']}/transition", json={"status_id": by_name[step]})).status_code == 200
    r = await client.post(f"/api/v1/tasks/{task_a['id']}/transition", json={"status_id": by_name["Done"]})
    assert r.json()["detail"]["code"] == "RESULT_NOT_REVIEWED"

    # ── Третий участник проверяет конкретные результаты ─────────────────────
    act_as(reviewer)
    queue = {q["task"]["key"] for q in (await client.get("/api/v1/review-queue")).json()}
    assert queue == {task_a["key"], task_b["key"]}
    ok = {"verdict": "accepted", "rationale": "PR проверен, тесты зелёные",
          "criteria": [{"key": "c1", "verdict": "met"}]}
    assert (await client.post(f"/api/v1/proposals/{first.json()['id']}/reviews", json=ok)).status_code == 201
    r = await client.post(f"/api/v1/proposals/{pb['id']}/reviews", json={
        "verdict": "changes_requested", "rationale": "Нет теста на новую ветку",
        "criteria": [{"key": "c1", "verdict": "not_met", "note": "ветка else"}],
    })
    assert r.status_code == 201

    act_as(agent_b)
    pb2 = (await client.post(f"/api/v1/tasks/{task_b['id']}/proposals", json={
        "summary": "Добавлен тест", "criteria": [{"key": "c1", "status": "met"}], "supersedes_id": pb["id"],
    })).json()
    act_as(reviewer)
    assert (await client.post(f"/api/v1/proposals/{pb2['id']}/reviews", json=ok)).status_code == 201

    act_as(agent_a)
    assert (await client.post(f"/api/v1/tasks/{task_a['id']}/transition", json={"status_id": by_name["Done"]})).status_code == 200

    # ── Межпроектную поставку принимает получатель (факт записывает менеджер) ──
    await client.post(f"/api/v1/tasks/{task_a['id']}/delivery", json={"target": projects[1].key})
    act_as(manager)
    t = (await client.post(f"/api/v1/tasks/{task_a['id']}/recipient-acceptance", json={
        "accepted_by": f"{projects[1].key}: руководитель", "accepted_at": "2026-09-30T12:00:00Z", "source": "office",
    })).json()
    assert t["result_state"] == "accepted" and t["recipient_acceptance"]["recorded_by"] == str(manager.id)

    # ── Старое решение неприменимо: исследование с выводом «не применять» ───
    research = (await client.post(f"/api/v1/projects/{projects[0].id}/tasks", json={
        "title": "Применим ли старый артефакт X?", "task_type_key": "research", "assignee_id": str(agent_a.id),
    })).json()
    wf_r = (await client.get(f"/api/v1/workflows/{research['workflow_id']}")).json()
    rs = {s["name"]: s["id"] for s in wf_r["statuses"]}
    act_as(agent_a)
    await client.post(f"/api/v1/tasks/{research['id']}/transition", json={"status_id": rs["Investigating"]})
    research = (await client.get(f"/api/v1/tasks/{research['id']}")).json()
    await client.patch(f"/api/v1/tasks/{research['id']}", json={
        "meta": {"conclusion": "do_not_apply", "findings": "Формат устарел, пересборка дороже"},
        "version": research["version"],
    })
    pr = (await client.post(f"/api/v1/tasks/{research['id']}/proposals", json={"summary": "Не применять"})).json()
    act_as(reviewer)
    await client.post(f"/api/v1/proposals/{pr['id']}/reviews", json={
        "verdict": "accepted", "rationale": "Вывод подтверждён", "criteria": [],
    })
    act_as(agent_a)
    r = await client.post(f"/api/v1/tasks/{research['id']}/transition", json={"status_id": rs["Concluded"]})
    assert r.status_code == 200

    # ── История сохраняет авторов, сессии и причины ──────────────────────────
    act_as(manager)
    history = (await client.get(f"/api/v1/tasks/{task_b['id']}/history")).json()["items"]
    released = next(e for e in history if e["entity_type"] == "task_session" and e["action"] == "released")
    assert released["actor_id"] == str(manager.id)
    assert released["after"]["reason"] == "gpu-b проверен, процесс остановлен"
    reviews = [e for e in history if e["entity_type"] == "review"]
    assert [e["after"]["verdict"] for e in reviews] == ["changes_requested", "accepted"]
    assert all(e["actor_id"] == str(reviewer.id) for e in reviews)
