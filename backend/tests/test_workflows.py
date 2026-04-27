import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.schemas.project import ProjectCreate
from app.schemas.workflow import (
    ResolutionCreate,
    StatusCreate,
    TransitionCreate,
    WorkflowCreate,
)
from app.services import project_service, workflow_service


# --- helpers ---

async def _make_project(session: AsyncSession, user: User, key: str) -> str:
    p = await project_service.create_project(session, ProjectCreate(name=key, key=key), user)
    return str(p.id)


async def _make_workflow(client: AsyncClient, project_id: str, name: str = "WF") -> dict:
    r = await client.post(f"/api/v1/projects/{project_id}/workflows", json={"name": name, "is_default": True})
    assert r.status_code == 201
    return r.json()


async def _make_status(client: AsyncClient, wf_id: str, name: str, category: str, position: int = 0, is_default: bool = False) -> dict:
    r = await client.post(f"/api/v1/workflows/{wf_id}/statuses", json={
        "name": name, "category": category, "position": position, "is_default": is_default,
    })
    assert r.status_code == 201
    return r.json()


# --- tests ---

async def test_create_workflow(client: AsyncClient, db_session: AsyncSession, stub_user: User):
    pid = await _make_project(db_session, stub_user, "WF_CREATE")
    wf = await _make_workflow(client, pid, "Basic")
    assert wf["name"] == "Basic"
    assert wf["is_default"] is True
    assert wf["statuses"] == []


async def test_list_workflows(client: AsyncClient, db_session: AsyncSession, stub_user: User):
    pid = await _make_project(db_session, stub_user, "WF_LIST")
    await _make_workflow(client, pid, "WF1")
    await _make_workflow(client, pid, "WF2")

    r = await client.get(f"/api/v1/projects/{pid}/workflows")
    assert r.status_code == 200
    assert len(r.json()) == 2


async def test_create_statuses(client: AsyncClient, db_session: AsyncSession, stub_user: User):
    pid = await _make_project(db_session, stub_user, "WF_STAT")
    wf = await _make_workflow(client, pid)

    todo = await _make_status(client, wf["id"], "To Do", "initial", position=0, is_default=True)
    inprog = await _make_status(client, wf["id"], "In Progress", "intermediate", position=1)
    done = await _make_status(client, wf["id"], "Done", "final", position=2)

    r = await client.get(f"/api/v1/workflows/{wf['id']}")
    statuses = r.json()["statuses"]
    assert len(statuses) == 3
    names = {s["name"] for s in statuses}
    assert names == {"To Do", "In Progress", "Done"}


async def test_create_transition(client: AsyncClient, db_session: AsyncSession, stub_user: User):
    pid = await _make_project(db_session, stub_user, "WF_TRANS")
    wf = await _make_workflow(client, pid)
    todo = await _make_status(client, wf["id"], "To Do", "initial")
    inprog = await _make_status(client, wf["id"], "In Progress", "intermediate")

    r = await client.post(f"/api/v1/workflows/{wf['id']}/transitions", json={
        "from_status_id": todo["id"],
        "to_status_id": inprog["id"],
    })
    assert r.status_code == 201
    assert r.json()["from_status_id"] == todo["id"]
    assert r.json()["to_status_id"] == inprog["id"]


async def test_validate_transition_allowed(db_session: AsyncSession, stub_user: User):
    p = await project_service.create_project(db_session, ProjectCreate(name="VT", key="VT1"), stub_user)
    wf = await workflow_service.create_workflow(db_session, p.id, WorkflowCreate(name="WF"), stub_user)
    todo = await workflow_service.create_status(db_session, wf.id, StatusCreate(name="To Do", category="initial"), stub_user)
    inprog = await workflow_service.create_status(db_session, wf.id, StatusCreate(name="In Progress", category="intermediate"), stub_user)
    await workflow_service.create_transition(db_session, wf.id, TransitionCreate(from_status_id=todo.id, to_status_id=inprog.id), stub_user)

    assert await workflow_service.validate_transition(db_session, wf.id, todo.id, inprog.id) is True


async def test_validate_transition_not_allowed(db_session: AsyncSession, stub_user: User):
    p = await project_service.create_project(db_session, ProjectCreate(name="VT2", key="VT2"), stub_user)
    wf = await workflow_service.create_workflow(db_session, p.id, WorkflowCreate(name="WF"), stub_user)
    todo = await workflow_service.create_status(db_session, wf.id, StatusCreate(name="To Do", category="initial"), stub_user)
    done = await workflow_service.create_status(db_session, wf.id, StatusCreate(name="Done", category="final"), stub_user)
    # No transition created between todo and done

    assert await workflow_service.validate_transition(db_session, wf.id, todo.id, done.id) is False


async def test_delete_status(client: AsyncClient, db_session: AsyncSession, stub_user: User):
    pid = await _make_project(db_session, stub_user, "WF_DEL")
    wf = await _make_workflow(client, pid)
    s = await _make_status(client, wf["id"], "Temp", "intermediate")

    r = await client.delete(f"/api/v1/statuses/{s['id']}")
    assert r.status_code == 204

    wf_data = (await client.get(f"/api/v1/workflows/{wf['id']}")).json()
    assert all(st["id"] != s["id"] for st in wf_data["statuses"])


async def test_delete_status_cascades_transitions(client: AsyncClient, db_session: AsyncSession, stub_user: User):
    pid = await _make_project(db_session, stub_user, "WF_CASCADE")
    wf = await _make_workflow(client, pid)
    todo = await _make_status(client, wf["id"], "To Do", "initial")
    mid = await _make_status(client, wf["id"], "Mid", "intermediate")
    done = await _make_status(client, wf["id"], "Done", "final")

    await client.post(f"/api/v1/workflows/{wf['id']}/transitions", json={"from_status_id": todo["id"], "to_status_id": mid["id"]})
    await client.post(f"/api/v1/workflows/{wf['id']}/transitions", json={"from_status_id": mid["id"], "to_status_id": done["id"]})

    # Delete mid — both transitions referencing it should be removed
    r = await client.delete(f"/api/v1/statuses/{mid['id']}")
    assert r.status_code == 204

    wf_data = (await client.get(f"/api/v1/workflows/{wf['id']}")).json()
    assert wf_data["transitions"] == []


async def test_migrate_status(client: AsyncClient, db_session: AsyncSession, stub_user: User):
    pid = await _make_project(db_session, stub_user, "WF_MIGRATE")
    wf = await _make_workflow(client, pid)
    src = await _make_status(client, wf["id"], "Old Status", "intermediate")
    tgt = await _make_status(client, wf["id"], "New Status", "intermediate")

    r = await client.post(f"/api/v1/statuses/{src['id']}/migrate", json={"target_status_id": tgt["id"]})
    assert r.status_code == 200

    wf_data = (await client.get(f"/api/v1/workflows/{wf['id']}")).json()
    assert all(s["id"] != src["id"] for s in wf_data["statuses"])


async def test_create_resolution(client: AsyncClient, db_session: AsyncSession, stub_user: User):
    pid = await _make_project(db_session, stub_user, "WF_RES")

    r = await client.post(f"/api/v1/projects/{pid}/resolutions", json={"name": "Done", "is_default": True})
    assert r.status_code == 201
    assert r.json()["name"] == "Done"
    assert r.json()["is_default"] is True


async def test_list_resolutions(client: AsyncClient, db_session: AsyncSession, stub_user: User):
    pid = await _make_project(db_session, stub_user, "WF_RESLIST")
    await client.post(f"/api/v1/projects/{pid}/resolutions", json={"name": "Done", "is_default": True})
    await client.post(f"/api/v1/projects/{pid}/resolutions", json={"name": "Won't Fix"})

    r = await client.get(f"/api/v1/projects/{pid}/resolutions")
    assert r.status_code == 200
    assert len(r.json()) == 2


async def test_delete_resolution(client: AsyncClient, db_session: AsyncSession, stub_user: User):
    pid = await _make_project(db_session, stub_user, "WF_RESDEL")
    r = await client.post(f"/api/v1/projects/{pid}/resolutions", json={"name": "Temp"})
    rid = r.json()["id"]

    del_r = await client.delete(f"/api/v1/resolutions/{rid}")
    assert del_r.status_code == 204

    list_r = await client.get(f"/api/v1/projects/{pid}/resolutions")
    assert all(res["id"] != rid for res in list_r.json())
