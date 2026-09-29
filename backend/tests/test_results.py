"""Предложение результата и независимая проверка (FR-003, TT-14–17, ADR-016, ADR-021).

- исполнитель подаёт предложение результата по версии задания; оно неизменно,
  исправление — новая версия, которая требует новой проверки;
- проверяет только участник с профилем проверяющего, не автор и не исполнитель;
- принятие без основания и без выполнения обязательных критериев невозможно;
- выполнение, локальная проверка, предложение поставки и приёмка получателем —
  раздельные состояния;
- тип задачи с обязательной проверкой не закрывается без вердикта.
"""
import uuid

import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.main import app
from app.models.notification import Notification
from app.models.project import ProjectMember, ProjectMemberRole
from app.models.task_type import TaskType
from app.models.user import User
from app.models.workflow import Status, StatusCategory, Transition, Workflow
from app.schemas.project import ProjectCreate
from app.services import project_service

PACKAGE = {
    "goal": "Сделать отчёт",
    "expected_result": "Отчёт в формате PDF",
    "criteria": [{"text": "Все разделы заполнены"}, {"text": "Есть графики", "required": False}],
    "specialization": "analytics",
}


def act_as(user: User) -> None:
    app.dependency_overrides[get_current_user] = lambda: user


async def _user(session: AsyncSession, **kw) -> User:
    u = User(id=uuid.uuid4(), email=f"u_{uuid.uuid4().hex[:8]}@t.com", display_name="U",
             keycloak_id=str(uuid.uuid4()), is_active=True, **kw)
    session.add(u)
    await session.flush()
    return u


@pytest_asyncio.fixture
async def world(client: AsyncClient, db_session: AsyncSession, stub_user: User) -> dict:
    """Project owned by stub_user (manager-level admin), an assignee and a reviewer."""
    project = await project_service.create_project(
        db_session, ProjectCreate(name="Res", key=uuid.uuid4().hex[:8].upper()), stub_user
    )
    worker = await _user(db_session)
    reviewer = await _user(db_session)
    outsider_member = await _user(db_session)
    db_session.add_all([
        ProjectMember(project_id=project.id, user_id=worker.id, role=ProjectMemberRole.member),
        ProjectMember(project_id=project.id, user_id=reviewer.id, role=ProjectMemberRole.member),
        ProjectMember(project_id=project.id, user_id=outsider_member.id, role=ProjectMemberRole.member),
    ])
    await db_session.flush()
    r = await client.patch(f"/api/v1/projects/{project.id}/members/{reviewer.id}", json={"is_reviewer": True})
    assert r.status_code == 200, r.text

    task = (await client.post(f"/api/v1/projects/{project.id}/tasks", json={
        "title": "Report", "assignee_id": str(worker.id),
    })).json()
    url = f"/api/v1/tasks/{task['id']}/work-package"
    await client.put(f"{url}/draft", json=PACKAGE)
    package = (await client.post(f"{url}/issue")).json()
    return {"project": project, "task": task, "package": package,
            "worker": worker, "reviewer": reviewer, "member": outsider_member, "owner": stub_user}


def _proposal(**kw) -> dict:
    return {
        "summary": "Отчёт готов",
        "links": [{"kind": "pr", "url": "https://github.com/org/repo/pull/1"}],
        "criteria": [{"key": "c1", "status": "met", "evidence": "см. раздел 1–5"}],
        "checks": [{"name": "pdf-lint", "result": "passed"}],
        **kw,
    }


async def _submit(client, world, **kw) -> dict:
    act_as(world["worker"])
    r = await client.post(f"/api/v1/tasks/{world['task']['id']}/proposals", json=_proposal(**kw))
    assert r.status_code == 201, r.text
    return r.json()


async def _review(client, proposal_id, **body):
    return await client.post(f"/api/v1/proposals/{proposal_id}/reviews", json=body)


ACCEPT = {"verdict": "accepted", "rationale": "Все разделы на месте",
          "criteria": [{"key": "c1", "verdict": "met", "note": "проверено"}]}


# ── Подача ──────────────────────────────────────────────────────────────────

async def test_assignee_submits_proposal_for_current_package(client, world):
    p = await _submit(client, world)
    assert p["version"] == 1 and p["status"] == "submitted"
    assert p["work_package_id"] == world["package"]["id"]
    assert p["author_id"] == str(world["worker"].id)
    task = (await client.get(f"/api/v1/tasks/{world['task']['id']}")).json()
    assert task["result_state"] == "proposed"


async def test_only_assignee_submits(client, world):
    act_as(world["member"])
    r = await client.post(f"/api/v1/tasks/{world['task']['id']}/proposals", json=_proposal())
    assert r.status_code == 403
    assert r.json()["detail"]["code"] == "NOT_ASSIGNEE"


async def test_unknown_criterion_rejected(client, world):
    act_as(world["worker"])
    r = await client.post(f"/api/v1/tasks/{world['task']['id']}/proposals",
                          json=_proposal(criteria=[{"key": "zzz", "status": "met"}]))
    assert r.status_code == 422
    assert r.json()["detail"]["code"] == "UNKNOWN_CRITERION"


# ── Проверка ────────────────────────────────────────────────────────────────

async def test_reviewer_accepts(client, db_session, world):
    p = await _submit(client, world)
    act_as(world["reviewer"])
    r = await _review(client, p["id"], **ACCEPT)
    assert r.status_code == 201, r.text
    assert r.json()["reviewer_id"] == str(world["reviewer"].id)

    listed = (await client.get(f"/api/v1/tasks/{world['task']['id']}/proposals")).json()
    assert listed[0]["status"] == "accepted" and len(listed[0]["reviews"]) == 1
    task = (await client.get(f"/api/v1/tasks/{world['task']['id']}")).json()
    assert task["result_state"] == "accepted"

    notes = (await db_session.scalars(
        select(Notification).where(Notification.recipient_id == world["worker"].id)
    )).all()
    assert any(n.event_type.value == "review_completed" for n in notes)


async def test_author_and_assignee_cannot_review(client, db_session, world):
    p = await _submit(client, world)
    # даже с профилем проверяющего исполнитель не проверяет свою задачу
    act_as(world["owner"])
    await client.patch(f"/api/v1/projects/{world['project'].id}/members/{world['worker'].id}",
                       json={"is_reviewer": True})
    act_as(world["worker"])
    r = await _review(client, p["id"], **ACCEPT)
    assert r.status_code == 403
    assert r.json()["detail"]["code"] == "SELF_REVIEW"


async def test_member_without_reviewer_profile_cannot_review(client, world):
    p = await _submit(client, world)
    act_as(world["member"])
    r = await _review(client, p["id"], **ACCEPT)
    assert r.status_code == 403
    assert r.json()["detail"]["code"] == "NOT_REVIEWER"


async def test_designated_reviewer_only(client, db_session, world):
    other_reviewer = await _user(db_session)
    db_session.add(ProjectMember(project_id=world["project"].id, user_id=other_reviewer.id,
                                 role=ProjectMemberRole.member, is_reviewer=True))
    await db_session.flush()
    act_as(world["owner"])
    task = (await client.get(f"/api/v1/tasks/{world['task']['id']}")).json()
    r = await client.patch(f"/api/v1/tasks/{task['id']}", json={
        "reviewer_id": str(world["reviewer"].id), "version": task["version"],
    })
    assert r.status_code == 200, r.text

    p = await _submit(client, world)
    act_as(other_reviewer)
    r = await _review(client, p["id"], **ACCEPT)
    assert r.status_code == 403
    assert r.json()["detail"]["code"] == "NOT_DESIGNATED_REVIEWER"


async def test_designated_reviewer_must_have_profile(client, world):
    act_as(world["owner"])
    task = (await client.get(f"/api/v1/tasks/{world['task']['id']}")).json()
    r = await client.patch(f"/api/v1/tasks/{task['id']}", json={
        "reviewer_id": str(world["member"].id), "version": task["version"],
    })
    assert r.status_code == 400
    assert r.json()["detail"]["code"] == "NOT_REVIEWER"


async def test_accept_requires_required_criteria_met(client, world):
    p = await _submit(client, world)
    act_as(world["reviewer"])
    r = await _review(client, p["id"], verdict="accepted", rationale="ок", criteria=[])
    assert r.status_code == 422
    assert r.json()["detail"]["code"] == "CRITERIA_NOT_MET"
    assert r.json()["detail"]["criteria"] == ["c1"]

    r = await _review(client, p["id"], verdict="accepted", rationale="ок",
                      criteria=[{"key": "c1", "verdict": "not_met", "note": "нет раздела 3"}])
    assert r.status_code == 422


async def test_rationale_required(client, world):
    p = await _submit(client, world)
    act_as(world["reviewer"])
    r = await _review(client, p["id"], verdict="rejected", rationale="   ", criteria=[])
    assert r.status_code == 422


async def test_changes_requested_then_new_version_needs_new_review(client, world):
    p1 = await _submit(client, world)
    act_as(world["reviewer"])
    r = await _review(client, p1["id"], verdict="changes_requested", rationale="Нет раздела 3",
                      criteria=[{"key": "c1", "verdict": "not_met", "note": "раздел 3"}])
    assert r.status_code == 201
    task = (await client.get(f"/api/v1/tasks/{world['task']['id']}")).json()
    assert task["result_state"] == "changes_requested"

    p2 = await _submit(client, world, summary="Добавлен раздел 3", supersedes_id=p1["id"])
    assert p2["version"] == 2 and p2["status"] == "submitted"
    task = (await client.get(f"/api/v1/tasks/{world['task']['id']}")).json()
    assert task["result_state"] == "proposed"

    # прежняя версия и её проверка остаются в истории, повторно её не проверить
    act_as(world["reviewer"])
    r = await _review(client, p1["id"], **ACCEPT)
    assert r.status_code == 409
    assert r.json()["detail"]["code"] == "PROPOSAL_NOT_REVIEWABLE"
    listed = (await client.get(f"/api/v1/tasks/{world['task']['id']}/proposals")).json()
    by_version = {p["version"]: p for p in listed}
    assert by_version[1]["status"] == "superseded" and len(by_version[1]["reviews"]) == 1
    assert (await _review(client, p2["id"], **ACCEPT)).status_code == 201


async def test_proposal_is_immutable_and_withdrawable(client, world):
    p = await _submit(client, world)
    act_as(world["worker"])
    assert (await client.patch(f"/api/v1/proposals/{p['id']}", json={"summary": "x"})).status_code == 405
    r = await client.post(f"/api/v1/proposals/{p['id']}/withdraw")
    assert r.status_code == 200 and r.json()["status"] == "withdrawn"
    task = (await client.get(f"/api/v1/tasks/{world['task']['id']}")).json()
    assert task["result_state"] == "none"


# ── Состояния: выполнение, проверка, поставка, приёмка получателем ─────────

async def test_delivery_and_recipient_acceptance_are_separate_facts(client, world):
    tid = world["task"]["id"]
    p = await _submit(client, world)

    act_as(world["worker"])
    r = await client.post(f"/api/v1/tasks/{tid}/delivery", json={"target": "project OFFICE"})
    assert r.status_code == 409
    assert r.json()["detail"]["code"] == "RESULT_NOT_ACCEPTED"

    act_as(world["reviewer"])
    await _review(client, p["id"], **ACCEPT)

    act_as(world["worker"])
    r = await client.post(f"/api/v1/tasks/{tid}/delivery", json={"target": "project OFFICE", "ref": "REL-7"})
    assert r.status_code == 200
    assert r.json()["delivery"]["proposal_id"] == p["id"]
    assert r.json()["recipient_acceptance"] is None

    # приёмку получателем фиксирует менеджер как полученный факт — не исполнитель
    r = await client.post(f"/api/v1/tasks/{tid}/recipient-acceptance", json={
        "accepted_by": "Office: Иванов", "accepted_at": "2026-09-30T10:00:00Z", "source": "office", "ref": "DEC-12",
    })
    assert r.status_code == 403
    act_as(world["owner"])
    r = await client.post(f"/api/v1/tasks/{tid}/recipient-acceptance", json={
        "accepted_by": "Office: Иванов", "accepted_at": "2026-09-30T10:00:00Z", "source": "office", "ref": "DEC-12",
    })
    assert r.status_code == 200
    ra = r.json()["recipient_acceptance"]
    assert ra["accepted_by"] == "Office: Иванов" and ra["recorded_by"] == str(world["owner"].id)
    assert r.json()["result_state"] == "accepted"


# ── Закрытие задачи требует вердикта проверки ───────────────────────────────

async def test_review_required_type_blocks_final_transition(client, db_session, world):
    tt = await db_session.scalar(select(TaskType).where(TaskType.key == "task", TaskType.project_id.is_(None)))
    tt.requires_review = True
    await db_session.flush()
    tid = world["task"]["id"]
    wf_id = world["task"]["workflow_id"]
    statuses = (await db_session.scalars(select(Status).where(Status.workflow_id == uuid.UUID(wf_id)))).all()
    initial = next(s for s in statuses if s.is_default)
    final = next(s for s in statuses if s.category == StatusCategory.final)
    db_session.add(Transition(workflow_id=uuid.UUID(wf_id), from_status_id=initial.id, to_status_id=final.id))
    await db_session.flush()

    act_as(world["worker"])
    r = await client.post(f"/api/v1/tasks/{tid}/transition", json={"status_id": str(final.id)})
    assert r.status_code == 400
    assert r.json()["detail"]["code"] == "RESULT_NOT_REVIEWED"

    p = await _submit(client, world)
    act_as(world["reviewer"])
    await _review(client, p["id"], verdict="rejected", rationale="Подход неприменим: данных нет", criteria=[])
    act_as(world["worker"])
    r = await client.post(f"/api/v1/tasks/{tid}/transition", json={"status_id": str(final.id)})
    assert r.status_code == 200  # аргументированный отказ тоже завершает работу


# ── Суррогат Decision Process заменён ───────────────────────────────────────

async def test_decision_task_waits_for_subtask_results(client, db_session, stub_user):
    project = await project_service.create_project(
        db_session, ProjectCreate(name="Dec", key=uuid.uuid4().hex[:8].upper()), stub_user
    )
    wf = await db_session.scalar(select(Workflow).where(Workflow.project_id == project.id))
    inprog = await db_session.scalar(select(Status).where(Status.workflow_id == wf.id, Status.name == "In Progress"))
    parent = (await client.post(f"/api/v1/projects/{project.id}/tasks", json={
        "title": "Choose", "task_type_key": "decision", "assignee_id": str(stub_user.id),
    })).json()
    sub = (await client.post(f"/api/v1/projects/{project.id}/tasks", json={
        "title": "Option A", "parent_task_id": parent["id"], "assignee_id": str(stub_user.id),
    })).json()

    r = await client.post(f"/api/v1/tasks/{parent['id']}/transition", json={"status_id": str(inprog.id)})
    assert r.status_code == 400 and r.json()["detail"]["code"] == "TASK_BLOCKED_BY_SUBTASKS"

    # комментарий с меткой solution больше ничего не значит
    await client.post(f"/api/v1/tasks/{sub['id']}/comments", json={"content": "вариант", "labels": ["solution"]})
    r = await client.post(f"/api/v1/tasks/{parent['id']}/transition", json={"status_id": str(inprog.id)})
    assert r.status_code == 400

    r = await client.post(f"/api/v1/tasks/{sub['id']}/proposals", json={"summary": "Вариант A"})
    assert r.status_code == 201
    r = await client.post(f"/api/v1/tasks/{parent['id']}/transition", json={"status_id": str(inprog.id)})
    assert r.status_code == 200


async def test_proposal_and_review_are_audited(client, world):
    p = await _submit(client, world)
    act_as(world["reviewer"])
    await _review(client, p["id"], **ACCEPT)
    history = (await client.get(f"/api/v1/tasks/{world['task']['id']}/history")).json()["items"]
    kinds = [(e["entity_type"], e["action"]) for e in history]
    assert ("result_proposal", "created") in kinds
    assert ("review", "created") in kinds
