import uuid

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.models.workflow import StatusCategory
from app.schemas.project import ProjectCreate
from app.schemas.workflow import (
    StatusCreate,
    TransitionCreate,
    WorkflowCreate,
)
from app.services import project_service, workflow_service


def _rnd_key() -> str:
    """Random 8-char uppercase hex key — avoids UNIQUE conflicts between tests."""
    return uuid.uuid4().hex[:8].upper()


async def _make_project(session: AsyncSession, user: User) -> str:
    p = await project_service.create_project(
        session, ProjectCreate(name="Test", key=_rnd_key()), user
    )
    return str(p.id)


async def _make_workflow(client: AsyncClient, project_id: str, name: str = "WF") -> dict:
    r = await client.post(
        f"/api/v1/projects/{project_id}/workflows",
        json={"name": name, "is_default": True},
    )
    assert r.status_code == 201
    return r.json()


async def _make_status(
    client: AsyncClient,
    wf_id: str,
    name: str,
    category: StatusCategory,
    position: int = 0,
    is_default: bool = False,
) -> dict:
    r = await client.post(
        f"/api/v1/workflows/{wf_id}/statuses",
        json={
            "name": name,
            "category": category.value,
            "position": position,
            "is_default": is_default,
        },
    )
    assert r.status_code == 201
    return r.json()


# --- tests ---

async def test_create_workflow(client: AsyncClient, db_session: AsyncSession, stub_user: User):
    pid = await _make_project(db_session, stub_user)
    wf = await _make_workflow(client, pid, "Basic")
    assert wf["name"] == "Basic"
    assert wf["is_default"] is True
    assert wf["statuses"] == []
    assert "created_at" in wf


async def test_list_workflows(client: AsyncClient, db_session: AsyncSession, stub_user: User):
    pid = await _make_project(db_session, stub_user)
    # project auto-creates "Basic" workflow; add 2 more
    await _make_workflow(client, pid, "WF1")
    await _make_workflow(client, pid, "WF2")
    r = await client.get(f"/api/v1/projects/{pid}/workflows")
    assert r.status_code == 200
    names = [w["name"] for w in r.json()]
    assert "WF1" in names
    assert "WF2" in names


async def test_create_statuses_with_timestamps(
    client: AsyncClient, db_session: AsyncSession, stub_user: User
):
    pid = await _make_project(db_session, stub_user)
    wf = await _make_workflow(client, pid)
    todo = await _make_status(client, wf["id"], "To Do", StatusCategory.initial, is_default=True)
    await _make_status(client, wf["id"], "In Progress", StatusCategory.intermediate, position=1)
    await _make_status(client, wf["id"], "Done", StatusCategory.final, position=2)

    r = await client.get(f"/api/v1/workflows/{wf['id']}")
    statuses = r.json()["statuses"]
    assert len(statuses) == 3
    assert all("created_at" in s for s in statuses)
    assert todo["is_default"] is True


async def test_status_default_must_be_initial(
    client: AsyncClient, db_session: AsyncSession, stub_user: User
):
    pid = await _make_project(db_session, stub_user)
    wf = await _make_workflow(client, pid)
    r = await client.post(f"/api/v1/workflows/{wf['id']}/statuses", json={
        "name": "Done",
        "category": StatusCategory.final.value,
        "is_default": True,
    })
    assert r.status_code == 400
    assert r.json()["detail"]["code"] == "STATUS_DEFAULT_MUST_BE_INITIAL"


async def test_status_default_unique_per_workflow(
    client: AsyncClient, db_session: AsyncSession, stub_user: User
):
    pid = await _make_project(db_session, stub_user)
    wf = await _make_workflow(client, pid)
    await _make_status(client, wf["id"], "To Do", StatusCategory.initial, is_default=True)
    # Second default status should unset the first
    s2 = await _make_status(client, wf["id"], "Backlog", StatusCategory.initial, is_default=True)
    assert s2["is_default"] is True

    wf_data = (await client.get(f"/api/v1/workflows/{wf['id']}")).json()
    defaults = [s for s in wf_data["statuses"] if s["is_default"]]
    assert len(defaults) == 1
    assert defaults[0]["id"] == s2["id"]


async def test_create_transition(
    client: AsyncClient, db_session: AsyncSession, stub_user: User
):
    pid = await _make_project(db_session, stub_user)
    wf = await _make_workflow(client, pid)
    todo = await _make_status(client, wf["id"], "To Do", StatusCategory.initial)
    inprog = await _make_status(client, wf["id"], "In Progress", StatusCategory.intermediate)

    r = await client.post(f"/api/v1/workflows/{wf['id']}/transitions", json={
        "from_status_id": todo["id"],
        "to_status_id": inprog["id"],
    })
    assert r.status_code == 201
    assert "created_at" in r.json()


async def test_create_transition_rejects_cross_workflow_statuses(
    client: AsyncClient, db_session: AsyncSession, stub_user: User
):
    pid = await _make_project(db_session, stub_user)
    wf1 = await _make_workflow(client, pid, "WF1")
    wf2_r = await client.post(f"/api/v1/projects/{pid}/workflows", json={"name": "WF2"})
    wf2 = wf2_r.json()

    s1 = await _make_status(client, wf1["id"], "A", StatusCategory.initial)
    s2 = await _make_status(client, wf2["id"], "B", StatusCategory.initial)

    r = await client.post(f"/api/v1/workflows/{wf1['id']}/transitions", json={
        "from_status_id": s1["id"],
        "to_status_id": s2["id"],
    })
    assert r.status_code == 400
    assert r.json()["detail"]["code"] == "STATUS_NOT_IN_WORKFLOW"


async def test_validate_transition_allowed(db_session: AsyncSession, stub_user: User):
    p = await project_service.create_project(
        db_session, ProjectCreate(name="VT", key=_rnd_key()), stub_user
    )
    wf = await workflow_service.create_workflow(
        db_session, p.id, WorkflowCreate(name="WF"), stub_user
    )
    todo = await workflow_service.create_status(
        db_session, wf.id, StatusCreate(name="To Do", category=StatusCategory.initial), stub_user
    )
    inprog = await workflow_service.create_status(
        db_session, wf.id,
        StatusCreate(name="In Progress", category=StatusCategory.intermediate), stub_user
    )
    await workflow_service.create_transition(
        db_session, wf.id,
        TransitionCreate(from_status_id=todo.id, to_status_id=inprog.id), stub_user
    )

    assert await workflow_service.validate_transition(db_session, wf.id, todo.id, inprog.id) is True


async def test_validate_transition_not_allowed(db_session: AsyncSession, stub_user: User):
    p = await project_service.create_project(
        db_session, ProjectCreate(name="VT2", key=_rnd_key()), stub_user
    )
    wf = await workflow_service.create_workflow(
        db_session, p.id, WorkflowCreate(name="WF"), stub_user
    )
    todo = await workflow_service.create_status(
        db_session, wf.id, StatusCreate(name="To Do", category=StatusCategory.initial), stub_user
    )
    done = await workflow_service.create_status(
        db_session, wf.id, StatusCreate(name="Done", category=StatusCategory.final), stub_user
    )

    assert await workflow_service.validate_transition(db_session, wf.id, todo.id, done.id) is False


async def test_delete_status_cascades_transitions(
    client: AsyncClient, db_session: AsyncSession, stub_user: User
):
    pid = await _make_project(db_session, stub_user)
    wf = await _make_workflow(client, pid)
    todo = await _make_status(client, wf["id"], "To Do", StatusCategory.initial)
    mid = await _make_status(client, wf["id"], "Mid", StatusCategory.intermediate)
    done = await _make_status(client, wf["id"], "Done", StatusCategory.final)

    await client.post(f"/api/v1/workflows/{wf['id']}/transitions",
                      json={"from_status_id": todo["id"], "to_status_id": mid["id"]})
    await client.post(f"/api/v1/workflows/{wf['id']}/transitions",
                      json={"from_status_id": mid["id"], "to_status_id": done["id"]})

    r = await client.delete(f"/api/v1/statuses/{mid['id']}")
    assert r.status_code == 204

    wf_data = (await client.get(f"/api/v1/workflows/{wf['id']}")).json()
    assert wf_data["transitions"] == []


async def test_migrate_status(
    client: AsyncClient, db_session: AsyncSession, stub_user: User
):
    pid = await _make_project(db_session, stub_user)
    wf = await _make_workflow(client, pid)
    src = await _make_status(client, wf["id"], "Old", StatusCategory.intermediate)
    tgt = await _make_status(client, wf["id"], "New", StatusCategory.intermediate)

    r = await client.post(f"/api/v1/statuses/{src['id']}/migrate",
                          json={"target_status_id": tgt["id"]})
    assert r.status_code == 200

    wf_data = (await client.get(f"/api/v1/workflows/{wf['id']}")).json()
    assert all(s["id"] != src["id"] for s in wf_data["statuses"])


async def test_delete_default_workflow_blocked(
    client: AsyncClient, db_session: AsyncSession, stub_user: User
):
    pid = await _make_project(db_session, stub_user)
    wf = await _make_workflow(client, pid)  # is_default=True
    r = await client.delete(f"/api/v1/workflows/{wf['id']}")
    assert r.status_code == 409
    assert r.json()["detail"]["code"] == "WORKFLOW_IS_DEFAULT"


async def test_create_resolution_with_position(
    client: AsyncClient, db_session: AsyncSession, stub_user: User
):
    pid = await _make_project(db_session, stub_user)
    r = await client.post(f"/api/v1/projects/{pid}/resolutions",
                          json={"name": "Done", "is_default": True, "position": 0})
    assert r.status_code == 201
    data = r.json()
    assert data["is_default"] is True
    assert "created_at" in data


async def test_resolution_default_upsert(
    client: AsyncClient, db_session: AsyncSession, stub_user: User
):
    pid = await _make_project(db_session, stub_user)
    r1 = await client.post(f"/api/v1/projects/{pid}/resolutions",
                           json={"name": "Done", "is_default": True})
    r2 = await client.post(f"/api/v1/projects/{pid}/resolutions",
                           json={"name": "Won't Fix", "is_default": True})

    list_r = await client.get(f"/api/v1/projects/{pid}/resolutions")
    defaults = [r for r in list_r.json() if r["is_default"]]
    assert len(defaults) == 1
    assert defaults[0]["id"] == r2.json()["id"]


async def test_list_resolutions(
    client: AsyncClient, db_session: AsyncSession, stub_user: User
):
    pid = await _make_project(db_session, stub_user)
    # project auto-creates 3 resolutions; add a custom one and verify it appears
    await client.post(f"/api/v1/projects/{pid}/resolutions", json={"name": "Custom", "position": 10})

    r = await client.get(f"/api/v1/projects/{pid}/resolutions")
    assert r.status_code == 200
    names = [res["name"] for res in r.json()]
    assert "Custom" in names
    assert "Done" in names


async def test_delete_resolution(
    client: AsyncClient, db_session: AsyncSession, stub_user: User
):
    pid = await _make_project(db_session, stub_user)
    r = await client.post(f"/api/v1/projects/{pid}/resolutions", json={"name": "Temp"})
    rid = r.json()["id"]

    del_r = await client.delete(f"/api/v1/resolutions/{rid}")
    assert del_r.status_code == 204

    list_r = await client.get(f"/api/v1/projects/{pid}/resolutions")
    assert all(res["id"] != rid for res in list_r.json())


async def test_status_color(client: AsyncClient, db_session: AsyncSession, stub_user: User):
    pid = await _make_project(db_session, stub_user)
    wf = await _make_workflow(client, pid)
    s = await _make_status(client, wf["id"], "To Do", StatusCategory.initial)

    r = await client.patch(f"/api/v1/statuses/{s['id']}", json={"color": "#3B82F6"})
    assert r.status_code == 200
    assert r.json()["color"] == "#3B82F6"

    wf_data = (await client.get(f"/api/v1/workflows/{wf['id']}")).json()
    assert wf_data["statuses"][0]["color"] == "#3B82F6"


async def test_migrate_status_reassigns_assignments(
    client: AsyncClient, db_session: AsyncSession, stub_user: User
):
    from app.schemas.project import ProjectCreate
    from app.schemas.workflow import WorkflowCreate, StatusCreate
    from app.schemas.task import AssignmentCreate
    from app.services import task_service

    project = await project_service.create_project(
        db_session, ProjectCreate(name="Migrate", key=_rnd_key()), stub_user
    )
    wf = await workflow_service.create_workflow(
        db_session, project.id, WorkflowCreate(name="WF"), stub_user
    )
    src = await workflow_service.create_status(
        db_session, wf.id, StatusCreate(name="Old", category=StatusCategory.initial, is_default=True), stub_user
    )
    tgt = await workflow_service.create_status(
        db_session, wf.id, StatusCreate(name="New", category=StatusCategory.intermediate), stub_user
    )
    await db_session.flush()

    from app.schemas.task import TaskCreate
    task = await task_service.create_task(
        db_session, project.id,
        TaskCreate(title="T", workflow_id=wf.id), stub_user
    )
    assignment = await task_service.assign_user(
        db_session, task.id,
        AssignmentCreate(user_id=stub_user.id), stub_user
    )
    assert assignment.current_status_id == src.id

    r = await client.post(f"/api/v1/statuses/{src.id}/migrate",
                          json={"target_status_id": str(tgt.id)})
    assert r.status_code == 200

    await db_session.refresh(assignment)
    assert assignment.current_status_id == tgt.id


async def test_delete_status_with_active_assignment(
    client: AsyncClient, db_session: AsyncSession, stub_user: User
):
    from app.schemas.task import TaskCreate, AssignmentCreate
    from app.services import task_service

    pid = await _make_project(db_session, stub_user)
    wf = await _make_workflow(client, pid)
    todo = await _make_status(client, wf["id"], "To Do", StatusCategory.initial, is_default=True)
    await _make_status(client, wf["id"], "Done", StatusCategory.final, position=1)

    task = await task_service.create_task(
        db_session, uuid.UUID(pid),
        TaskCreate(title="T", workflow_id=uuid.UUID(wf["id"])), stub_user
    )
    await task_service.assign_user(
        db_session, task.id,
        AssignmentCreate(user_id=stub_user.id), stub_user
    )

    r = await client.delete(f"/api/v1/statuses/{todo['id']}")
    assert r.status_code == 409
    assert r.json()["detail"]["code"] == "STATUS_HAS_ACTIVE_ASSIGNMENTS"


async def test_delete_workflow_with_tasks_blocked(
    client: AsyncClient, db_session: AsyncSession, stub_user: User
):
    from app.schemas.project import ProjectCreate
    from app.schemas.workflow import WorkflowCreate, StatusCreate
    from app.schemas.task import TaskCreate
    from app.services import task_service

    project = await project_service.create_project(
        db_session, ProjectCreate(name="WFDel", key=_rnd_key()), stub_user
    )
    wf_non_default = await workflow_service.create_workflow(
        db_session, project.id, WorkflowCreate(name="Secondary", is_default=False), stub_user
    )
    await workflow_service.create_status(
        db_session, wf_non_default.id,
        StatusCreate(name="To Do", category=StatusCategory.initial, is_default=True), stub_user
    )
    await task_service.create_task(
        db_session, project.id,
        TaskCreate(title="T", workflow_id=wf_non_default.id), stub_user
    )

    r = await client.delete(f"/api/v1/workflows/{wf_non_default.id}")
    assert r.status_code == 409
    assert r.json()["detail"]["code"] == "WORKFLOW_HAS_TASKS"
