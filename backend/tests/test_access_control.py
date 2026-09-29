"""Единая проверка прав на изменение данных (FR-003, TT-01).

Чтение открыто всем, кто видит проект; изменение — только участникам с ролью
member и выше. Переход статуса: исполнитель или manager/admin, плюс
Transition.required_role как минимальная роль в проекте.
"""
import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.main import app
from app.models.link_type import LinkType
from app.models.project import ProjectMember, ProjectMemberRole, ProjectVisibility
from app.models.user import User
from app.models.workflow import Status, StatusCategory, Transition, Workflow
from app.schemas.project import ProjectCreate
from app.schemas.task import TaskCreate
from app.services import project_service, task_service


def _rnd_key() -> str:
    return uuid.uuid4().hex[:8].upper()


async def _make_user(session: AsyncSession) -> User:
    u = User(
        id=uuid.uuid4(), email=f"u_{uuid.uuid4().hex[:8]}@t.com", display_name="U",
        keycloak_id=str(uuid.uuid4()), is_active=True,
    )
    session.add(u)
    await session.flush()
    return u


async def _add_member(session: AsyncSession, project_id, user: User, role: ProjectMemberRole):
    session.add(ProjectMember(project_id=project_id, user_id=user.id, role=role))
    await session.flush()


def _act_as(user: User) -> None:
    app.dependency_overrides[get_current_user] = lambda: user


async def _setup(session: AsyncSession, owner: User, *, public: bool = True) -> dict:
    visibility = ProjectVisibility.public if public else ProjectVisibility.restricted
    project = await project_service.create_project(
        session, ProjectCreate(name="ACL", key=_rnd_key(), visibility=visibility), owner
    )
    task = await task_service.create_task(session, project.id, TaskCreate(title="T"), owner)
    other = await task_service.create_task(session, project.id, TaskCreate(title="T2"), owner)

    wf = await session.scalar(
        select(Workflow).where(Workflow.project_id == project.id, Workflow.is_default.is_(True))
    )
    statuses = list((await session.scalars(
        select(Status).where(Status.workflow_id == wf.id).order_by(Status.position)
    )).all())
    todo = next(s for s in statuses if s.is_default)
    inprog = next(s for s in statuses if s.name == "In Progress")
    done = next(s for s in statuses if s.category == StatusCategory.final)
    return {
        "project_id": project.id, "task": task, "other_task": other,
        "workflow_id": wf.id, "todo": todo, "inprog": inprog, "done": done,
    }


# ── Не участник публичного проекта: читает, но не меняет ─────────────────────

async def test_non_member_of_public_project_reads_but_cannot_write(
    client: AsyncClient, db_session: AsyncSession, stub_user: User
):
    ctx = await _setup(db_session, stub_user, public=True)
    task_id = ctx["task"].id
    lt = LinkType(name=f"lt-{uuid.uuid4().hex[:6]}", outward_name="blocks", inward_name="is blocked by")
    db_session.add(lt)
    await db_session.flush()

    outsider = await _make_user(db_session)
    _act_as(outsider)

    assert (await client.get(f"/api/v1/tasks/{task_id}")).status_code == 200
    assert (await client.get(f"/api/v1/tasks/{task_id}/comments")).status_code == 200

    writes = [
        await client.post(f"/api/v1/projects/{ctx['project_id']}/tasks", json={"title": "X"}),
        await client.patch(f"/api/v1/tasks/{task_id}", json={"title": "X", "version": 1}),
        await client.post(f"/api/v1/tasks/{task_id}/transition", json={"status_id": str(ctx["inprog"].id)}),
        await client.post(f"/api/v1/tasks/{task_id}/comments", json={"content": "X"}),
        await client.post(f"/api/v1/tasks/{task_id}/links", json={
            "target_task_id": str(ctx["other_task"].id), "link_type_id": str(lt.id),
        }),
        await client.delete(f"/api/v1/tasks/{task_id}"),
    ]
    for r in writes:
        assert r.status_code == 403, (r.request.method, r.request.url, r.text)
        assert r.json()["detail"]["code"] == "PERMISSION_DENIED"


async def test_viewer_reads_but_cannot_write(
    client: AsyncClient, db_session: AsyncSession, stub_user: User
):
    ctx = await _setup(db_session, stub_user, public=False)
    task_id = ctx["task"].id
    viewer = await _make_user(db_session)
    await _add_member(db_session, ctx["project_id"], viewer, ProjectMemberRole.viewer)
    _act_as(viewer)

    assert (await client.get(f"/api/v1/tasks/{task_id}")).status_code == 200

    writes = [
        await client.post(f"/api/v1/projects/{ctx['project_id']}/tasks", json={"title": "X"}),
        await client.patch(f"/api/v1/tasks/{task_id}", json={"title": "X", "version": 1}),
        await client.post(f"/api/v1/tasks/{task_id}/comments", json={"content": "X"}),
        await client.delete(f"/api/v1/tasks/{task_id}"),
    ]
    for r in writes:
        assert r.status_code == 403, (r.request.method, r.request.url, r.text)


async def test_viewer_assignee_cannot_transition(
    client: AsyncClient, db_session: AsyncSession, stub_user: User
):
    """Назначение не даёт прав выше роли в проекте."""
    ctx = await _setup(db_session, stub_user)
    viewer = await _make_user(db_session)
    await _add_member(db_session, ctx["project_id"], viewer, ProjectMemberRole.viewer)
    ctx["task"].assignee_id = viewer.id
    await db_session.flush()
    _act_as(viewer)

    r = await client.post(
        f"/api/v1/tasks/{ctx['task'].id}/transition", json={"status_id": str(ctx["inprog"].id)}
    )
    assert r.status_code == 403


async def test_member_can_write(
    client: AsyncClient, db_session: AsyncSession, stub_user: User
):
    ctx = await _setup(db_session, stub_user, public=False)
    member = await _make_user(db_session)
    await _add_member(db_session, ctx["project_id"], member, ProjectMemberRole.member)
    _act_as(member)

    r = await client.post(f"/api/v1/projects/{ctx['project_id']}/tasks", json={"title": "Mine"})
    assert r.status_code == 201
    r = await client.post(f"/api/v1/tasks/{ctx['task'].id}/comments", json={"content": "hi"})
    assert r.status_code == 201


# ── Переходы ─────────────────────────────────────────────────────────────────

async def test_member_cannot_transition_others_task(
    client: AsyncClient, db_session: AsyncSession, stub_user: User
):
    ctx = await _setup(db_session, stub_user)
    member = await _make_user(db_session)
    await _add_member(db_session, ctx["project_id"], member, ProjectMemberRole.member)
    _act_as(member)

    r = await client.post(
        f"/api/v1/tasks/{ctx['task'].id}/transition", json={"status_id": str(ctx["inprog"].id)}
    )
    assert r.status_code == 403
    assert r.json()["detail"]["code"] == "PERMISSION_DENIED"


async def test_manager_can_transition_others_task(
    client: AsyncClient, db_session: AsyncSession, stub_user: User
):
    ctx = await _setup(db_session, stub_user)
    manager = await _make_user(db_session)
    await _add_member(db_session, ctx["project_id"], manager, ProjectMemberRole.manager)
    _act_as(manager)

    r = await client.post(
        f"/api/v1/tasks/{ctx['task'].id}/transition", json={"status_id": str(ctx["inprog"].id)}
    )
    assert r.status_code == 200
    assert r.json()["current_status_id"] == str(ctx["inprog"].id)


@pytest.mark.parametrize("required, actor_role, expected", [
    ("manager", ProjectMemberRole.member, 403),
    ("manager", ProjectMemberRole.manager, 200),
    ("admin", ProjectMemberRole.manager, 403),
    ("reviewer", ProjectMemberRole.admin, 403),  # неизвестная роль — отказ
])
async def test_transition_required_role(
    client: AsyncClient, db_session: AsyncSession, stub_user: User,
    required: str, actor_role: ProjectMemberRole, expected: int,
):
    ctx = await _setup(db_session, stub_user)
    tr = await db_session.scalar(select(Transition).where(
        Transition.workflow_id == ctx["workflow_id"],
        Transition.from_status_id == ctx["todo"].id,
        Transition.to_status_id == ctx["inprog"].id,
    ))
    tr.required_role = required

    actor = await _make_user(db_session)
    await _add_member(db_session, ctx["project_id"], actor, actor_role)
    ctx["task"].assignee_id = actor.id
    await db_session.flush()
    _act_as(actor)

    r = await client.post(
        f"/api/v1/tasks/{ctx['task'].id}/transition", json={"status_id": str(ctx["inprog"].id)}
    )
    assert r.status_code == expected, r.text
    if expected == 403:
        assert r.json()["detail"]["code"] == "TRANSITION_ROLE_REQUIRED"


# ── Суррогат Solution ────────────────────────────────────────────────────────

async def test_solution_label_only_by_assignee(
    client: AsyncClient, db_session: AsyncSession, stub_user: User
):
    ctx = await _setup(db_session, stub_user)
    assignee = await _make_user(db_session)
    stranger = await _make_user(db_session)
    await _add_member(db_session, ctx["project_id"], assignee, ProjectMemberRole.member)
    await _add_member(db_session, ctx["project_id"], stranger, ProjectMemberRole.member)
    ctx["task"].assignee_id = assignee.id
    await db_session.flush()
    url = f"/api/v1/tasks/{ctx['task'].id}/comments"

    _act_as(stranger)
    r = await client.post(url, json={"content": "мой вариант", "labels": ["solution"]})
    assert r.status_code == 403
    assert r.json()["detail"]["code"] == "SOLUTION_NOT_ASSIGNEE"

    _act_as(assignee)
    r = await client.post(url, json={"content": "мой вариант", "labels": ["solution"]})
    assert r.status_code == 201


# ── Гант ─────────────────────────────────────────────────────────────────────

async def test_gantt_mutations_only_by_owner(
    client: AsyncClient, db_session: AsyncSession, stub_user: User
):
    ctx = await _setup(db_session, stub_user)
    r = await client.post("/api/v1/gantt", json={"name": "Plan"})
    gantt_id = r.json()["id"]
    task_id = str(ctx["task"].id)
    assert (await client.post(f"/api/v1/gantt/{gantt_id}/tasks", json={"task_id": task_id})).status_code == 204

    stranger = await _make_user(db_session)
    await _add_member(db_session, ctx["project_id"], stranger, ProjectMemberRole.admin)
    _act_as(stranger)

    writes = [
        await client.patch(f"/api/v1/gantt/{gantt_id}", json={"name": "Mine"}),
        await client.patch(f"/api/v1/gantt/{gantt_id}/tasks/reorder", json={"task_ids": [task_id]}),
        await client.post(f"/api/v1/gantt/{gantt_id}/tasks", json={"task_id": str(ctx["other_task"].id)}),
        await client.delete(f"/api/v1/gantt/{gantt_id}/tasks/{task_id}"),
        await client.delete(f"/api/v1/gantt/{gantt_id}"),
    ]
    for r in writes:
        assert r.status_code == 403, (r.request.method, r.request.url, r.text)

    # Чтение по-прежнему доступно
    assert (await client.get(f"/api/v1/gantt/{gantt_id}/tasks")).status_code == 200


async def test_gantt_hides_tasks_of_invisible_projects(
    client: AsyncClient, db_session: AsyncSession, stub_user: User
):
    visible = await _setup(db_session, stub_user, public=True)
    hidden = await _setup(db_session, stub_user, public=False)
    r = await client.post("/api/v1/gantt", json={"name": "Mixed"})
    gantt_id = r.json()["id"]
    for t in (visible["task"], hidden["task"]):
        await client.post(f"/api/v1/gantt/{gantt_id}/tasks", json={"task_id": str(t.id)})

    outsider = await _make_user(db_session)
    _act_as(outsider)

    ids = {t["id"] for t in (await client.get(f"/api/v1/gantt/{gantt_id}/tasks")).json()}
    assert ids == {str(visible["task"].id)}
