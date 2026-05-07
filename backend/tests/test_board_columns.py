"""Tests for BoardColumn CRUD via View-based API."""
import uuid

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.project import Project, ProjectMember, ProjectMemberRole, ProjectVisibility
from app.models.user import User
from app.schemas.project import ProjectCreate
from app.services import project_service


async def _setup(session: AsyncSession, user: User) -> tuple[str, str, str, str]:
    """Returns (project_id, view_id, workflow_id, status_id_todo)."""
    from sqlalchemy import select
    from app.models.workflow import View, ViewType, Workflow, Status

    p = await project_service.create_project(
        session, ProjectCreate(name="BC Test", key=uuid.uuid4().hex[:8].upper()), user
    )
    kanban_view = await session.scalar(
        select(View).where(View.project_id == p.id, View.type == ViewType.kanban)
    )
    wf = await session.scalar(
        select(Workflow).where(Workflow.project_id == p.id, Workflow.is_default.is_(True))
    )
    todo = await session.scalar(
        select(Status).where(Status.workflow_id == wf.id, Status.is_default.is_(True))
    )
    return str(p.id), str(kanban_view.id), str(wf.id), str(todo.id)


async def _make_member_project(session: AsyncSession, stub_user: User) -> tuple[str, str]:
    """Project where stub_user is plain member (not manager). Returns (project_id, view_id)."""
    from sqlalchemy import select
    from app.models.workflow import View, ViewType

    owner = User(
        id=uuid.uuid4(), email=f"owner_{uuid.uuid4().hex[:6]}@t.com",
        display_name="Owner", keycloak_id=f"kc-{uuid.uuid4().hex[:8]}", is_active=True,
    )
    session.add(owner)
    await session.flush()
    p = await project_service.create_project(
        session, ProjectCreate(name="Member Project", key=uuid.uuid4().hex[:8].upper()), owner
    )
    session.add(ProjectMember(project_id=p.id, user_id=stub_user.id, role=ProjectMemberRole.member))
    await session.flush()
    kanban_view = await session.scalar(
        select(View).where(View.project_id == p.id, View.type == ViewType.kanban)
    )
    return str(p.id), str(kanban_view.id)


async def test_get_board_columns_empty(client: AsyncClient, db_session: AsyncSession, stub_user: User):
    pid, vid, _, _ = await _setup(db_session, stub_user)

    r = await client.get(f"/api/v1/views/{vid}/columns")
    assert r.status_code == 200
    assert r.json()["items"] == []


async def test_create_board_column(client: AsyncClient, db_session: AsyncSession, stub_user: User):
    pid, vid, _, _ = await _setup(db_session, stub_user)

    r = await client.post(f"/api/v1/views/{vid}/columns", json={"name": "Backlog", "position": 0})
    assert r.status_code == 201
    col = r.json()
    assert col["name"] == "Backlog"
    assert col["status_ids"] == []

    list_r = await client.get(f"/api/v1/views/{vid}/columns")
    assert len(list_r.json()["items"]) == 1


async def test_add_status_to_column(client: AsyncClient, db_session: AsyncSession, stub_user: User):
    pid, vid, _, todo_id = await _setup(db_session, stub_user)

    col_r = await client.post(f"/api/v1/views/{vid}/columns", json={"name": "Col1", "position": 0})
    col_id = col_r.json()["id"]

    r = await client.post(f"/api/v1/board-columns/{col_id}/statuses", json={"status_id": todo_id})
    assert r.status_code == 200
    assert todo_id in r.json()["status_ids"]


async def test_status_in_one_column_only(client: AsyncClient, db_session: AsyncSession, stub_user: User):
    pid, vid, _, todo_id = await _setup(db_session, stub_user)

    col1_r = await client.post(f"/api/v1/views/{vid}/columns", json={"name": "Col1", "position": 0})
    col2_r = await client.post(f"/api/v1/views/{vid}/columns", json={"name": "Col2", "position": 1})
    col1_id = col1_r.json()["id"]
    col2_id = col2_r.json()["id"]

    await client.post(f"/api/v1/board-columns/{col1_id}/statuses", json={"status_id": todo_id})

    r = await client.post(f"/api/v1/board-columns/{col2_id}/statuses", json={"status_id": todo_id})
    assert r.status_code == 409
    assert r.json()["detail"]["code"] == "STATUS_ALREADY_MAPPED"


async def test_remove_status_from_column(client: AsyncClient, db_session: AsyncSession, stub_user: User):
    pid, vid, _, todo_id = await _setup(db_session, stub_user)

    col_r = await client.post(f"/api/v1/views/{vid}/columns", json={"name": "Col", "position": 0})
    col_id = col_r.json()["id"]
    await client.post(f"/api/v1/board-columns/{col_id}/statuses", json={"status_id": todo_id})

    del_r = await client.delete(f"/api/v1/board-columns/{col_id}/statuses/{todo_id}")
    assert del_r.status_code == 204

    col_get = await client.get(f"/api/v1/views/{vid}/columns")
    col = next(c for c in col_get.json()["items"] if c["id"] == col_id)
    assert todo_id not in col["status_ids"]


async def test_update_column_name_and_position(client: AsyncClient, db_session: AsyncSession, stub_user: User):
    pid, vid, _, _ = await _setup(db_session, stub_user)

    col_r = await client.post(f"/api/v1/views/{vid}/columns", json={"name": "Old", "position": 0})
    col_id = col_r.json()["id"]

    r = await client.patch(f"/api/v1/board-columns/{col_id}", json={"name": "New", "position": 5})
    assert r.status_code == 200
    assert r.json()["name"] == "New"
    assert r.json()["position"] == 5


async def test_delete_column(client: AsyncClient, db_session: AsyncSession, stub_user: User):
    pid, vid, _, _ = await _setup(db_session, stub_user)

    col_r = await client.post(f"/api/v1/views/{vid}/columns", json={"name": "ToDelete", "position": 0})
    col_id = col_r.json()["id"]

    del_r = await client.delete(f"/api/v1/board-columns/{col_id}")
    assert del_r.status_code == 204

    list_r = await client.get(f"/api/v1/views/{vid}/columns")
    assert all(c["id"] != col_id for c in list_r.json()["items"])


async def test_board_columns_require_manager_role(
    client: AsyncClient, db_session: AsyncSession, stub_user: User
):
    """Member (not manager) cannot create board columns."""
    _, vid = await _make_member_project(db_session, stub_user)

    r = await client.post(f"/api/v1/views/{vid}/columns", json={"name": "X", "position": 0})
    assert r.status_code == 403


async def test_delete_status_cascades_board_column(
    client: AsyncClient, db_session: AsyncSession, stub_user: User
):
    """Deleting a status removes it from BoardColumnStatus (CASCADE)."""
    pid, vid, wf_id, _ = await _setup(db_session, stub_user)

    new_s_r = await client.post(f"/api/v1/workflows/{wf_id}/statuses", json={
        "name": "Cascadable", "category": "intermediate", "position": 10
    })
    assert new_s_r.status_code == 201
    new_status_id = new_s_r.json()["id"]

    col_r = await client.post(f"/api/v1/views/{vid}/columns", json={"name": "CC", "position": 0})
    col_id = col_r.json()["id"]
    await client.post(f"/api/v1/board-columns/{col_id}/statuses", json={"status_id": new_status_id})

    await client.delete(f"/api/v1/statuses/{new_status_id}")

    list_r = await client.get(f"/api/v1/views/{vid}/columns")
    col = next(c for c in list_r.json()["items"] if c["id"] == col_id)
    assert new_status_id not in col["status_ids"]


async def test_create_project_auto_creates_views(client: AsyncClient):
    """New project gets Board (kanban) and Backlog views automatically."""
    r = await client.post("/api/v1/projects", json={"name": "Views Test", "key": "VTEST1"})
    assert r.status_code == 201
    pid = r.json()["id"]

    views_r = await client.get(f"/api/v1/projects/{pid}/views")
    assert views_r.status_code == 200
    views = views_r.json()
    assert len(views) == 2
    types = {v["type"] for v in views}
    assert types == {"kanban", "backlog"}
    default_views = [v for v in views if v["is_default"]]
    assert len(default_views) == 1
    assert default_views[0]["type"] == "kanban"
