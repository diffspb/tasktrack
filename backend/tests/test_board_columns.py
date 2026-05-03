"""Tests for BoardColumn and BoardColumnStatus CRUD."""
import uuid

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.project import Project, ProjectMember, ProjectMemberRole, ProjectVisibility
from app.models.user import User
from app.schemas.project import ProjectCreate
from app.services import project_service


async def _setup(session: AsyncSession, user: User) -> tuple[str, str, str]:
    """Returns (project_id, workflow_id, status_id_todo)."""
    from sqlalchemy import select
    from app.models.workflow import Workflow, Status

    p = await project_service.create_project(
        session, ProjectCreate(name="BC Test", key=uuid.uuid4().hex[:8].upper()), user
    )
    wf = await session.scalar(
        select(Workflow).where(Workflow.project_id == p.id, Workflow.is_default.is_(True))
    )
    todo = await session.scalar(
        select(Status).where(Status.workflow_id == wf.id, Status.is_default.is_(True))
    )
    return str(p.id), str(wf.id), str(todo.id)


async def _make_member_project(session: AsyncSession, stub_user: User) -> str:
    """Project where stub_user is plain member (not manager)."""
    owner = User(
        id=uuid.uuid4(), email=f"owner_{uuid.uuid4().hex[:6]}@t.com",
        display_name="Owner", keycloak_id=f"kc-{uuid.uuid4().hex[:8]}", is_active=True,
    )
    session.add(owner)
    await session.flush()
    p = Project(
        name="Member Project", key=uuid.uuid4().hex[:8].upper(),
        visibility=ProjectVisibility.restricted, owner_id=owner.id,
    )
    session.add(p)
    await session.flush()
    session.add(ProjectMember(project_id=p.id, user_id=owner.id, role=ProjectMemberRole.admin))
    session.add(ProjectMember(project_id=p.id, user_id=stub_user.id, role=ProjectMemberRole.member))
    await session.flush()
    return str(p.id)


async def test_get_board_columns_empty(client: AsyncClient, db_session: AsyncSession, stub_user: User):
    from app.models.project import Project, ProjectMember, ProjectMemberRole, ProjectVisibility
    project = Project(
        name="Empty BC", key=uuid.uuid4().hex[:8].upper(),
        visibility=ProjectVisibility.restricted, owner_id=stub_user.id,
    )
    db_session.add(project)
    await db_session.flush()
    db_session.add(ProjectMember(project_id=project.id, user_id=stub_user.id, role=ProjectMemberRole.admin))
    await db_session.flush()

    r = await client.get(f"/api/v1/projects/{project.id}/board-columns")
    assert r.status_code == 200
    assert r.json()["items"] == []


async def test_create_board_column(client: AsyncClient, db_session: AsyncSession, stub_user: User):
    pid, _, _ = await _setup(db_session, stub_user)

    r = await client.post(f"/api/v1/projects/{pid}/board-columns", json={"name": "Backlog", "position": 0})
    assert r.status_code == 201
    col = r.json()
    assert col["name"] == "Backlog"
    assert col["status_ids"] == []

    list_r = await client.get(f"/api/v1/projects/{pid}/board-columns")
    assert len(list_r.json()["items"]) == 1


async def test_add_status_to_column(client: AsyncClient, db_session: AsyncSession, stub_user: User):
    pid, _, todo_id = await _setup(db_session, stub_user)

    col_r = await client.post(f"/api/v1/projects/{pid}/board-columns", json={"name": "Col1", "position": 0})
    col_id = col_r.json()["id"]

    r = await client.post(f"/api/v1/board-columns/{col_id}/statuses", json={"status_id": todo_id})
    assert r.status_code == 200
    assert todo_id in r.json()["status_ids"]


async def test_status_in_one_column_only(client: AsyncClient, db_session: AsyncSession, stub_user: User):
    pid, _, todo_id = await _setup(db_session, stub_user)

    col1_r = await client.post(f"/api/v1/projects/{pid}/board-columns", json={"name": "Col1", "position": 0})
    col2_r = await client.post(f"/api/v1/projects/{pid}/board-columns", json={"name": "Col2", "position": 1})
    col1_id = col1_r.json()["id"]
    col2_id = col2_r.json()["id"]

    await client.post(f"/api/v1/board-columns/{col1_id}/statuses", json={"status_id": todo_id})

    r = await client.post(f"/api/v1/board-columns/{col2_id}/statuses", json={"status_id": todo_id})
    assert r.status_code == 409
    assert r.json()["detail"]["code"] == "STATUS_ALREADY_MAPPED"


async def test_remove_status_from_column(client: AsyncClient, db_session: AsyncSession, stub_user: User):
    pid, _, todo_id = await _setup(db_session, stub_user)

    col_r = await client.post(f"/api/v1/projects/{pid}/board-columns", json={"name": "Col", "position": 0})
    col_id = col_r.json()["id"]
    await client.post(f"/api/v1/board-columns/{col_id}/statuses", json={"status_id": todo_id})

    del_r = await client.delete(f"/api/v1/board-columns/{col_id}/statuses/{todo_id}")
    assert del_r.status_code == 204

    col_get = await client.get(f"/api/v1/projects/{pid}/board-columns")
    col = next(c for c in col_get.json()["items"] if c["id"] == col_id)
    assert todo_id not in col["status_ids"]


async def test_update_column_name_and_position(client: AsyncClient, db_session: AsyncSession, stub_user: User):
    pid, _, _ = await _setup(db_session, stub_user)

    col_r = await client.post(f"/api/v1/projects/{pid}/board-columns", json={"name": "Old", "position": 0})
    col_id = col_r.json()["id"]

    r = await client.patch(f"/api/v1/board-columns/{col_id}", json={"name": "New", "position": 5})
    assert r.status_code == 200
    assert r.json()["name"] == "New"
    assert r.json()["position"] == 5


async def test_delete_column(client: AsyncClient, db_session: AsyncSession, stub_user: User):
    pid, _, _ = await _setup(db_session, stub_user)

    col_r = await client.post(f"/api/v1/projects/{pid}/board-columns", json={"name": "ToDelete", "position": 0})
    col_id = col_r.json()["id"]

    del_r = await client.delete(f"/api/v1/board-columns/{col_id}")
    assert del_r.status_code == 204

    list_r = await client.get(f"/api/v1/projects/{pid}/board-columns")
    assert all(c["id"] != col_id for c in list_r.json()["items"])


async def test_board_columns_require_manager_role(
    client: AsyncClient, db_session: AsyncSession, stub_user: User
):
    """Member (not manager) cannot create/update/delete board columns."""
    pid = await _make_member_project(db_session, stub_user)

    r = await client.post(f"/api/v1/projects/{pid}/board-columns", json={"name": "X", "position": 0})
    assert r.status_code == 403


async def test_delete_status_cascades_board_column(
    client: AsyncClient, db_session: AsyncSession, stub_user: User
):
    """Deleting a status removes it from BoardColumnStatus (CASCADE)."""
    pid, wf_id, _ = await _setup(db_session, stub_user)

    # Create a new status in the default workflow
    new_s_r = await client.post(f"/api/v1/workflows/{wf_id}/statuses", json={
        "name": "Cascadable", "category": "intermediate", "position": 10
    })
    assert new_s_r.status_code == 201
    new_status_id = new_s_r.json()["id"]

    # Map it to a column
    col_r = await client.post(f"/api/v1/projects/{pid}/board-columns", json={"name": "CC", "position": 0})
    col_id = col_r.json()["id"]
    await client.post(f"/api/v1/board-columns/{col_id}/statuses", json={"status_id": new_status_id})

    # Delete the status → BoardColumnStatus should cascade
    await client.delete(f"/api/v1/statuses/{new_status_id}")

    # Column should no longer contain that status_id
    list_r = await client.get(f"/api/v1/projects/{pid}/board-columns")
    col = next(c for c in list_r.json()["items"] if c["id"] == col_id)
    assert new_status_id not in col["status_ids"]
