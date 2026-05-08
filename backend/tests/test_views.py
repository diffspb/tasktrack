"""Tests for Views CRUD API."""
import uuid

from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.project import ProjectMember, ProjectMemberRole
from app.models.user import User
from app.models.workflow import View, ViewType
from app.schemas.project import ProjectCreate
from app.services import project_service


async def _setup(session: AsyncSession, user: User) -> dict:
    """Creates project; returns project_id, kanban_view_id, backlog_view_id, workflow_id, todo_id."""
    from app.models.workflow import Workflow, Status

    p = await project_service.create_project(
        session, ProjectCreate(name="Views Test", key=uuid.uuid4().hex[:8].upper()), user
    )
    kanban = await session.scalar(
        select(View).where(View.project_id == p.id, View.type == ViewType.kanban)
    )
    backlog = await session.scalar(
        select(View).where(View.project_id == p.id, View.type == ViewType.backlog)
    )
    wf = await session.scalar(
        select(Workflow).where(Workflow.project_id == p.id, Workflow.is_default.is_(True))
    )
    todo = await session.scalar(
        select(Status).where(Status.workflow_id == wf.id, Status.is_default.is_(True))
    )
    return {
        "project_id": str(p.id),
        "kanban_view_id": str(kanban.id),
        "backlog_view_id": str(backlog.id),
        "workflow_id": str(wf.id),
        "todo_id": str(todo.id),
    }


async def _member_project(session: AsyncSession, stub_user: User) -> dict:
    """Project owned by another user; stub_user is plain member."""
    owner = User(
        id=uuid.uuid4(), email=f"owner_{uuid.uuid4().hex[:6]}@t.com",
        display_name="Owner", keycloak_id=f"kc-{uuid.uuid4().hex[:8]}", is_active=True,
    )
    session.add(owner)
    await session.flush()
    p = await project_service.create_project(
        session, ProjectCreate(name="Member Proj", key=uuid.uuid4().hex[:8].upper()), owner
    )
    session.add(ProjectMember(project_id=p.id, user_id=stub_user.id, role=ProjectMemberRole.member))
    await session.flush()
    kanban = await session.scalar(
        select(View).where(View.project_id == p.id, View.type == ViewType.kanban)
    )
    return {"project_id": str(p.id), "kanban_view_id": str(kanban.id)}


# ── List / Get ────────────────────────────────────────────────────────────────

async def test_list_views_after_create_project(client: AsyncClient):
    r = await client.post("/api/v1/projects", json={"name": "LV Test", "key": "LVTEST1"})
    pid = r.json()["id"]

    r = await client.get(f"/api/v1/projects/{pid}/views")
    assert r.status_code == 200
    views = r.json()
    assert len(views) == 2
    assert {v["type"] for v in views} == {"kanban", "backlog"}


async def test_get_view(client: AsyncClient, db_session: AsyncSession, stub_user: User):
    ctx = await _setup(db_session, stub_user)

    r = await client.get(f"/api/v1/views/{ctx['kanban_view_id']}")
    assert r.status_code == 200
    v = r.json()
    assert v["id"] == ctx["kanban_view_id"]
    assert v["type"] == "kanban"
    assert v["is_default"] is True


async def test_get_view_not_found(client: AsyncClient):
    r = await client.get(f"/api/v1/views/{uuid.uuid4()}")
    assert r.status_code == 404
    assert r.json()["detail"]["code"] == "VIEW_NOT_FOUND"


# ── Create ────────────────────────────────────────────────────────────────────

async def test_create_view(client: AsyncClient, db_session: AsyncSession, stub_user: User):
    ctx = await _setup(db_session, stub_user)

    r = await client.post(f"/api/v1/projects/{ctx['project_id']}/views", json={
        "name": "Sprint Board", "type": "kanban",
    })
    assert r.status_code == 201
    v = r.json()
    assert v["name"] == "Sprint Board"
    assert v["type"] == "kanban"
    assert v["is_default"] is False

    list_r = await client.get(f"/api/v1/projects/{ctx['project_id']}/views")
    assert len(list_r.json()) == 3


async def test_create_view_auto_position(client: AsyncClient, db_session: AsyncSession, stub_user: User):
    ctx = await _setup(db_session, stub_user)

    r = await client.post(f"/api/v1/projects/{ctx['project_id']}/views", json={
        "name": "Epic Tree", "type": "epic_tree",
    })
    assert r.status_code == 201
    assert r.json()["position"] == 2  # project starts with 2 views at positions 0 and 1


async def test_create_view_explicit_position(client: AsyncClient, db_session: AsyncSession, stub_user: User):
    ctx = await _setup(db_session, stub_user)

    r = await client.post(f"/api/v1/projects/{ctx['project_id']}/views", json={
        "name": "Pinned", "type": "backlog", "position": 99,
    })
    assert r.status_code == 201
    assert r.json()["position"] == 99


async def test_create_view_requires_manager(client: AsyncClient, db_session: AsyncSession, stub_user: User):
    ctx = await _member_project(db_session, stub_user)

    r = await client.post(f"/api/v1/projects/{ctx['project_id']}/views", json={
        "name": "Denied", "type": "kanban",
    })
    assert r.status_code == 403


# ── Update ────────────────────────────────────────────────────────────────────

async def test_update_view_name(client: AsyncClient, db_session: AsyncSession, stub_user: User):
    ctx = await _setup(db_session, stub_user)

    r = await client.patch(f"/api/v1/views/{ctx['backlog_view_id']}", json={"name": "Renamed Backlog"})
    assert r.status_code == 200
    assert r.json()["name"] == "Renamed Backlog"


async def test_update_view_position(client: AsyncClient, db_session: AsyncSession, stub_user: User):
    ctx = await _setup(db_session, stub_user)

    r = await client.patch(f"/api/v1/views/{ctx['backlog_view_id']}", json={"position": 10})
    assert r.status_code == 200
    assert r.json()["position"] == 10


async def test_update_view_requires_manager(client: AsyncClient, db_session: AsyncSession, stub_user: User):
    ctx = await _member_project(db_session, stub_user)

    r = await client.patch(f"/api/v1/views/{ctx['kanban_view_id']}", json={"name": "Hacked"})
    assert r.status_code == 403


async def test_update_view_not_found(client: AsyncClient):
    r = await client.patch(f"/api/v1/views/{uuid.uuid4()}", json={"name": "Ghost"})
    assert r.status_code == 404
    assert r.json()["detail"]["code"] == "VIEW_NOT_FOUND"


# ── Delete ────────────────────────────────────────────────────────────────────

async def test_delete_view(client: AsyncClient, db_session: AsyncSession, stub_user: User):
    ctx = await _setup(db_session, stub_user)

    r = await client.delete(f"/api/v1/views/{ctx['backlog_view_id']}")
    assert r.status_code == 204

    list_r = await client.get(f"/api/v1/projects/{ctx['project_id']}/views")
    ids = [v["id"] for v in list_r.json()]
    assert ctx["backlog_view_id"] not in ids


async def test_delete_default_view_blocked(client: AsyncClient, db_session: AsyncSession, stub_user: User):
    ctx = await _setup(db_session, stub_user)

    r = await client.delete(f"/api/v1/views/{ctx['kanban_view_id']}")
    assert r.status_code == 409
    assert r.json()["detail"]["code"] == "VIEW_IS_DEFAULT"


async def test_delete_view_cascades_columns(client: AsyncClient, db_session: AsyncSession, stub_user: User):
    """Columns belonging to a deleted view are cascade-deleted."""
    ctx = await _setup(db_session, stub_user)
    vid = ctx["backlog_view_id"]

    col_r = await client.post(f"/api/v1/views/{vid}/columns", json={"name": "Col", "position": 0})
    assert col_r.status_code == 201

    await client.delete(f"/api/v1/views/{vid}")

    # Columns endpoint should now 404 because view is gone
    r = await client.get(f"/api/v1/views/{vid}/columns")
    assert r.status_code == 404


async def test_delete_view_requires_manager(client: AsyncClient, db_session: AsyncSession, stub_user: User):
    ctx = await _member_project(db_session, stub_user)

    r = await client.delete(f"/api/v1/views/{ctx['kanban_view_id']}")
    assert r.status_code == 403


async def test_delete_view_not_found(client: AsyncClient):
    r = await client.delete(f"/api/v1/views/{uuid.uuid4()}")
    assert r.status_code == 404
    assert r.json()["detail"]["code"] == "VIEW_NOT_FOUND"


# ── Cross-view status uniqueness ──────────────────────────────────────────────

async def test_same_status_allowed_in_different_views(
    client: AsyncClient, db_session: AsyncSession, stub_user: User
):
    """The same status can be mapped into columns of two different views (cross-view allowed)."""
    ctx = await _setup(db_session, stub_user)
    status_id = ctx["todo_id"]

    # Add column to kanban view, map status there
    col1_r = await client.post(
        f"/api/v1/views/{ctx['kanban_view_id']}/columns",
        json={"name": "KanbanCol", "position": 0},
    )
    col1_id = col1_r.json()["id"]
    r1 = await client.post(f"/api/v1/board-columns/{col1_id}/statuses", json={"status_id": status_id})
    assert r1.status_code == 200

    # Add column to backlog view, map the SAME status there — must succeed
    col2_r = await client.post(
        f"/api/v1/views/{ctx['backlog_view_id']}/columns",
        json={"name": "BacklogCol", "position": 0},
    )
    col2_id = col2_r.json()["id"]
    r2 = await client.post(f"/api/v1/board-columns/{col2_id}/statuses", json={"status_id": status_id})
    assert r2.status_code == 200, r2.json()


async def test_same_status_blocked_within_same_view(
    client: AsyncClient, db_session: AsyncSession, stub_user: User
):
    """The same status cannot be in two columns of the same view."""
    ctx = await _setup(db_session, stub_user)
    status_id = ctx["todo_id"]

    col1_r = await client.post(
        f"/api/v1/views/{ctx['kanban_view_id']}/columns",
        json={"name": "Col1", "position": 0},
    )
    col2_r = await client.post(
        f"/api/v1/views/{ctx['kanban_view_id']}/columns",
        json={"name": "Col2", "position": 1},
    )
    await client.post(f"/api/v1/board-columns/{col1_r.json()['id']}/statuses", json={"status_id": status_id})

    r = await client.post(
        f"/api/v1/board-columns/{col2_r.json()['id']}/statuses", json={"status_id": status_id}
    )
    assert r.status_code == 409
    assert r.json()["detail"]["code"] == "STATUS_ALREADY_MAPPED"
