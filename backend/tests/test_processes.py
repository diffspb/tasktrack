"""Процессы исполнения, исследования, миграции; валидация метаданных (FR-003, TT-13, ADR-023).

- метаданные задачи проверяются по JSON Schema её типа;
- переход требует заполненных полей (Transition.required_fields) и полномочий;
- системные процессы создаются идемпотентно; исследование завершается
  выводом («не применять» — законный итог), а не фиктивной реализацией.
"""
import uuid

from httpx import AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.bootstrap import PROCESS_TYPES, ensure_process_types
from app.main import app
from app.models.project import ProjectMember, ProjectMemberRole
from app.models.task_type import TaskType
from app.models.user import User
from app.models.workflow import Status, StatusCategory, Transition, Workflow
from app.schemas.project import ProjectCreate
from app.services import project_service


async def _project(session: AsyncSession, owner: User):
    return await project_service.create_project(
        session, ProjectCreate(name="Proc", key=uuid.uuid4().hex[:8].upper()), owner
    )


async def test_process_types_are_idempotent(db_session: AsyncSession):
    await ensure_process_types(db_session)
    await ensure_process_types(db_session)
    for key in PROCESS_TYPES:
        count = await db_session.scalar(select(func.count()).select_from(TaskType).where(
            TaskType.key == key, TaskType.project_id.is_(None)))
        assert count == 1, key
    research = await db_session.scalar(select(TaskType).where(TaskType.key == "research"))
    assert research.requires_review and research.meta_schema["properties"]["conclusion"]


async def test_meta_validated_against_type_schema(client: AsyncClient, db_session: AsyncSession, stub_user: User):
    await ensure_process_types(db_session)
    project = await _project(db_session, stub_user)
    url = f"/api/v1/projects/{project.id}/tasks"

    r = await client.post(url, json={"title": "R", "task_type_key": "research", "meta": {"conclusion": "maybe"}})
    assert r.status_code == 422
    detail = r.json()["detail"]
    assert detail["code"] == "META_INVALID" and detail["errors"][0]["path"] == "conclusion"

    task = (await client.post(url, json={"title": "R", "task_type_key": "research"})).json()
    r = await client.patch(f"/api/v1/tasks/{task['id']}", json={"meta": {"conclusion": 42}, "version": task["version"]})
    assert r.status_code == 422
    r = await client.patch(f"/api/v1/tasks/{task['id']}", json={
        "meta": {"conclusion": "do_not_apply", "findings": "Данных недостаточно"}, "version": task["version"],
    })
    assert r.status_code == 200


async def test_transition_requires_fields(client: AsyncClient, db_session: AsyncSession, stub_user: User):
    project = await _project(db_session, stub_user)
    wf = await db_session.scalar(select(Workflow).where(Workflow.project_id == project.id))
    statuses = (await db_session.scalars(select(Status).where(Status.workflow_id == wf.id))).all()
    todo = next(s for s in statuses if s.is_default)
    inprog = next(s for s in statuses if s.name == "In Progress")
    tr = await db_session.scalar(select(Transition).where(
        Transition.from_status_id == todo.id, Transition.to_status_id == inprog.id))
    r = await client.patch(f"/api/v1/transitions/{tr.id}", json={"required_fields": ["estimate"]})
    assert r.status_code == 200, r.text
    assert r.json()["required_fields"] == ["estimate"]

    r = await client.post(f"/api/v1/workflows/{wf.id}/transitions", json={
        "from_status_id": str(inprog.id), "to_status_id": str(todo.id), "required_fields": ["", "x y"],
    })
    assert r.status_code == 422  # имена полей — идентификаторы

    task = (await client.post(f"/api/v1/projects/{project.id}/tasks", json={
        "title": "T", "assignee_id": str(stub_user.id),
    })).json()
    r = await client.post(f"/api/v1/tasks/{task['id']}/transition", json={"status_id": str(inprog.id)})
    assert r.status_code == 400
    assert r.json()["detail"] == {"code": "TRANSITION_FIELDS_REQUIRED", "missing": ["estimate"]}

    await client.patch(f"/api/v1/tasks/{task['id']}", json={"meta": {"estimate": ""}, "version": task["version"]})
    task = (await client.get(f"/api/v1/tasks/{task['id']}")).json()
    r = await client.post(f"/api/v1/tasks/{task['id']}/transition", json={"status_id": str(inprog.id)})
    assert r.status_code == 400  # пустое значение не считается заполненным

    await client.patch(f"/api/v1/tasks/{task['id']}", json={"meta": {"estimate": "3d"}, "version": task["version"]})
    r = await client.post(f"/api/v1/tasks/{task['id']}/transition", json={"status_id": str(inprog.id)})
    assert r.status_code == 200


async def test_research_concludes_with_do_not_apply(client: AsyncClient, db_session: AsyncSession, stub_user: User):
    """Исследование: вывод «не применять», проверенный проверяющим, — законное завершение."""
    await ensure_process_types(db_session)
    project = await _project(db_session, stub_user)
    researcher = User(id=uuid.uuid4(), email=f"r_{uuid.uuid4().hex[:6]}@t.com", display_name="R",
                      keycloak_id=str(uuid.uuid4()), is_active=True)
    db_session.add(researcher)
    await db_session.flush()
    db_session.add(ProjectMember(project_id=project.id, user_id=researcher.id, role=ProjectMemberRole.member))
    await db_session.flush()
    await client.patch(f"/api/v1/projects/{project.id}/members/{stub_user.id}", json={"is_reviewer": True})

    task = (await client.post(f"/api/v1/projects/{project.id}/tasks", json={
        "title": "Стоит ли переходить на X?", "task_type_key": "research", "assignee_id": str(researcher.id),
    })).json()
    statuses = {s.name: s for s in (await db_session.scalars(
        select(Status).where(Status.workflow_id == uuid.UUID(task["workflow_id"]))
    )).all()}
    concluded = statuses["Concluded"]
    assert concluded.category == StatusCategory.final

    app.dependency_overrides[get_current_user] = lambda: researcher
    await client.post(f"/api/v1/tasks/{task['id']}/transition", json={"status_id": str(statuses["Investigating"].id)})
    r = await client.post(f"/api/v1/tasks/{task['id']}/transition", json={"status_id": str(concluded.id)})
    assert r.status_code == 400 and r.json()["detail"]["code"] == "TRANSITION_FIELDS_REQUIRED"

    task = (await client.get(f"/api/v1/tasks/{task['id']}")).json()
    await client.patch(f"/api/v1/tasks/{task['id']}", json={
        "meta": {"conclusion": "do_not_apply", "findings": "Выигрыш < 5%, миграция дорогая"}, "version": task["version"],
    })
    r = await client.post(f"/api/v1/tasks/{task['id']}/transition", json={"status_id": str(concluded.id)})
    assert r.status_code == 400 and r.json()["detail"]["code"] == "RESULT_NOT_REVIEWED"

    p = (await client.post(f"/api/v1/tasks/{task['id']}/proposals", json={
        "summary": "Не применять: выигрыш < 5%", "links": [{"kind": "document", "url": "https://wiki/x"}],
    })).json()
    app.dependency_overrides[get_current_user] = lambda: stub_user
    r = await client.post(f"/api/v1/proposals/{p['id']}/reviews", json={
        "verdict": "accepted", "rationale": "Вывод обоснован замерами", "criteria": [],
    })
    assert r.status_code == 201, r.text

    app.dependency_overrides[get_current_user] = lambda: researcher
    r = await client.post(f"/api/v1/tasks/{task['id']}/transition", json={"status_id": str(concluded.id)})
    assert r.status_code == 200
