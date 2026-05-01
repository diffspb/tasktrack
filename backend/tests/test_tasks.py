import uuid

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.task import AssigneeRole, GlobalStatus, TaskPriority
from app.models.user import User
from app.models.workflow import StatusCategory
from app.schemas.project import ProjectCreate
from app.schemas.workflow import StatusCreate, TransitionCreate, WorkflowCreate
from app.services import project_service, workflow_service


def _rnd_key() -> str:
    return uuid.uuid4().hex[:8].upper()


async def _setup_project_and_workflow(session: AsyncSession, user: User) -> dict:
    """Creates project + workflow with To Do → In Progress → Done."""
    project = await project_service.create_project(
        session, ProjectCreate(name="Task Test", key=_rnd_key()), user
    )
    wf = await workflow_service.create_workflow(
        session, project.id, WorkflowCreate(name="Basic"), user
    )
    todo = await workflow_service.create_status(
        session, wf.id, StatusCreate(name="To Do", category=StatusCategory.initial, is_default=True), user
    )
    inprog = await workflow_service.create_status(
        session, wf.id, StatusCreate(name="In Progress", category=StatusCategory.intermediate, position=1), user
    )
    done = await workflow_service.create_status(
        session, wf.id, StatusCreate(name="Done", category=StatusCategory.final, position=2), user
    )
    await workflow_service.create_transition(
        session, wf.id, TransitionCreate(from_status_id=todo.id, to_status_id=inprog.id), user
    )
    await workflow_service.create_transition(
        session, wf.id, TransitionCreate(from_status_id=inprog.id, to_status_id=done.id), user
    )
    from app.schemas.resolution import ResolutionCreate
    from app.services import resolution_service
    resolution = await resolution_service.create_resolution(
        session, project.id, ResolutionCreate(name="Done", is_default=True), user
    )
    return {
        "project_id": str(project.id),
        "workflow_id": str(wf.id),
        "todo_id": str(todo.id),
        "inprog_id": str(inprog.id),
        "done_id": str(done.id),
        "resolution_id": str(resolution.id),
    }


async def test_create_task(client: AsyncClient, db_session: AsyncSession, stub_user: User):
    ctx = await _setup_project_and_workflow(db_session, stub_user)
    r = await client.post(f"/api/v1/projects/{ctx['project_id']}/tasks", json={
        "title": "My first task",
        "workflow_id": ctx["workflow_id"],
    })
    assert r.status_code == 201
    data = r.json()
    assert data["global_status"] == "open"
    assert data["key"].startswith(data["key"].split("-")[0])
    assert data["assignments"] == []
    assert data["version"] == 1


async def test_task_key_autoincrement(client: AsyncClient, db_session: AsyncSession, stub_user: User):
    ctx = await _setup_project_and_workflow(db_session, stub_user)
    pid = ctx["project_id"]
    wid = ctx["workflow_id"]
    r1 = await client.post(f"/api/v1/projects/{pid}/tasks", json={"title": "T1", "workflow_id": wid})
    r2 = await client.post(f"/api/v1/projects/{pid}/tasks", json={"title": "T2", "workflow_id": wid})
    key1 = r1.json()["key"]
    key2 = r2.json()["key"]
    num1 = int(key1.split("-")[-1])
    num2 = int(key2.split("-")[-1])
    assert num2 == num1 + 1


async def test_assign_lead_sets_in_progress(
    client: AsyncClient, db_session: AsyncSession, stub_user: User
):
    ctx = await _setup_project_and_workflow(db_session, stub_user)
    r = await client.post(f"/api/v1/projects/{ctx['project_id']}/tasks", json={
        "title": "Assign test", "workflow_id": ctx["workflow_id"],
    })
    task_id = r.json()["id"]

    a = await client.post(f"/api/v1/tasks/{task_id}/assignments", json={
        "user_id": str(stub_user.id), "role": "lead",
    })
    assert a.status_code == 201
    assert a.json()["role"] == "lead"
    assert a.json()["current_status_id"] == ctx["todo_id"]

    task = (await client.get(f"/api/v1/tasks/{task_id}")).json()
    assert task["global_status"] == "in_progress"


async def test_full_workflow_s1(
    client: AsyncClient, db_session: AsyncSession, stub_user: User
):
    """S1: create → assign → To Do → In Progress → Done → closed."""
    ctx = await _setup_project_and_workflow(db_session, stub_user)

    r = await client.post(f"/api/v1/projects/{ctx['project_id']}/tasks", json={
        "title": "S1 Task", "workflow_id": ctx["workflow_id"],
    })
    task_id = r.json()["id"]

    a = await client.post(f"/api/v1/tasks/{task_id}/assignments", json={
        "user_id": str(stub_user.id), "role": "lead",
    })
    assignment_id = a.json()["id"]

    # To Do → In Progress
    r1 = await client.patch(f"/api/v1/assignments/{assignment_id}/status", json={
        "status_id": ctx["inprog_id"],
    })
    assert r1.status_code == 200
    assert r1.json()["current_status_id"] == ctx["inprog_id"]

    # In Progress → Done (requires resolution)
    r2 = await client.patch(f"/api/v1/assignments/{assignment_id}/status", json={
        "status_id": ctx["done_id"],
        "resolution_id": ctx["resolution_id"],
    })
    assert r2.status_code == 200

    task = (await client.get(f"/api/v1/tasks/{task_id}")).json()
    assert task["global_status"] == "closed"


async def test_transition_not_allowed(
    client: AsyncClient, db_session: AsyncSession, stub_user: User
):
    ctx = await _setup_project_and_workflow(db_session, stub_user)
    r = await client.post(f"/api/v1/projects/{ctx['project_id']}/tasks", json={
        "title": "T", "workflow_id": ctx["workflow_id"],
    })
    task_id = r.json()["id"]
    a = await client.post(f"/api/v1/tasks/{task_id}/assignments", json={
        "user_id": str(stub_user.id), "role": "lead",
    })
    assignment_id = a.json()["id"]

    # Try To Do → Done directly — no such transition
    r = await client.patch(f"/api/v1/assignments/{assignment_id}/status", json={
        "status_id": ctx["done_id"], "resolution_id": ctx["resolution_id"],
    })
    assert r.status_code == 400
    assert r.json()["detail"]["code"] == "WORKFLOW_TRANSITION_NOT_ALLOWED"


async def test_resolution_required(
    client: AsyncClient, db_session: AsyncSession, stub_user: User
):
    ctx = await _setup_project_and_workflow(db_session, stub_user)
    r = await client.post(f"/api/v1/projects/{ctx['project_id']}/tasks", json={
        "title": "T", "workflow_id": ctx["workflow_id"],
    })
    task_id = r.json()["id"]
    a = await client.post(f"/api/v1/tasks/{task_id}/assignments", json={
        "user_id": str(stub_user.id), "role": "lead",
    })
    assignment_id = a.json()["id"]
    await client.patch(f"/api/v1/assignments/{assignment_id}/status",
                       json={"status_id": ctx["inprog_id"]})

    r = await client.patch(f"/api/v1/assignments/{assignment_id}/status", json={
        "status_id": ctx["done_id"],  # no resolution_id
    })
    assert r.status_code == 400
    assert r.json()["detail"]["code"] == "RESOLUTION_REQUIRED"


async def test_soft_delete_task(
    client: AsyncClient, db_session: AsyncSession, stub_user: User
):
    ctx = await _setup_project_and_workflow(db_session, stub_user)
    r = await client.post(f"/api/v1/projects/{ctx['project_id']}/tasks", json={
        "title": "To delete", "workflow_id": ctx["workflow_id"],
    })
    task_id = r.json()["id"]

    del_r = await client.delete(f"/api/v1/tasks/{task_id}")
    assert del_r.status_code == 204

    get_r = await client.get(f"/api/v1/tasks/{task_id}")
    assert get_r.status_code == 404


async def test_version_conflict(
    client: AsyncClient, db_session: AsyncSession, stub_user: User
):
    ctx = await _setup_project_and_workflow(db_session, stub_user)
    r = await client.post(f"/api/v1/projects/{ctx['project_id']}/tasks", json={
        "title": "Versioned", "workflow_id": ctx["workflow_id"],
    })
    task_id = r.json()["id"]

    r = await client.patch(f"/api/v1/tasks/{task_id}", json={
        "title": "Updated", "version": 99,
    })
    assert r.status_code == 409
    assert r.json()["detail"]["code"] == "VERSION_CONFLICT"


async def test_list_tasks_with_filter(
    client: AsyncClient, db_session: AsyncSession, stub_user: User
):
    ctx = await _setup_project_and_workflow(db_session, stub_user)
    pid = ctx["project_id"]
    wid = ctx["workflow_id"]

    r1 = await client.post(f"/api/v1/projects/{pid}/tasks", json={"title": "Open", "workflow_id": wid})
    task_id = r1.json()["id"]
    a = await client.post(f"/api/v1/tasks/{task_id}/assignments", json={
        "user_id": str(stub_user.id), "role": "lead",
    })
    await client.post(f"/api/v1/projects/{pid}/tasks", json={"title": "Another open", "workflow_id": wid})

    open_r = await client.get(f"/api/v1/projects/{pid}/tasks?global_status=open")
    inprog_r = await client.get(f"/api/v1/projects/{pid}/tasks?global_status=in_progress")
    assert any(t["id"] == task_id for t in inprog_r.json())
    assert all(t["global_status"] == "open" for t in open_r.json())


async def test_multi_lead_final_status_does_not_trigger_awaiting_decision(
    client: AsyncClient, db_session: AsyncSession, stub_user: User
):
    """Phase-6 semantics: workflow personal status alone doesn't move
    a multi-lead task to awaiting_decision. Only Solution.submit does."""
    ctx = await _setup_project_and_workflow(db_session, stub_user)

    other = User(id=uuid.uuid4(), email="other2@test.com",
                 display_name="Other", keycloak_id="other2-kc", is_active=True)
    db_session.add(other)
    await db_session.flush()

    from app.models.project import ProjectMember, ProjectMemberRole
    db_session.add(ProjectMember(
        project_id=uuid.UUID(ctx["project_id"]),
        user_id=other.id,
        role=ProjectMemberRole.member,
    ))
    await db_session.commit()

    r = await client.post(f"/api/v1/projects/{ctx['project_id']}/tasks", json={
        "title": "Multi lead", "workflow_id": ctx["workflow_id"],
    })
    task_id = r.json()["id"]

    a1 = await client.post(f"/api/v1/tasks/{task_id}/assignments", json={
        "user_id": str(stub_user.id), "role": "lead",
    })
    from app.services import task_service as ts
    from app.schemas.task import AssignmentCreate, AssignmentTransition
    a2 = await ts.assign_user(
        db_session, uuid.UUID(task_id),
        AssignmentCreate(user_id=other.id, role=AssigneeRole.lead), stub_user
    )

    a1_id = a1.json()["id"]
    await client.patch(f"/api/v1/assignments/{a1_id}/status", json={"status_id": ctx["inprog_id"]})
    await client.patch(f"/api/v1/assignments/{a1_id}/status", json={
        "status_id": ctx["done_id"], "resolution_id": ctx["resolution_id"],
    })

    await ts.transition_assignment_status(
        db_session, a2.id,
        AssignmentTransition(status_id=uuid.UUID(ctx["inprog_id"])), other,
    )
    await ts.transition_assignment_status(
        db_session, a2.id,
        AssignmentTransition(
            status_id=uuid.UUID(ctx["done_id"]),
            resolution_id=uuid.UUID(ctx["resolution_id"]),
        ), other,
    )

    task = (await client.get(f"/api/v1/tasks/{task_id}")).json()
    assert task["global_status"] == "in_progress"


async def test_transition_other_user_assignment_forbidden(
    client: AsyncClient, db_session: AsyncSession, stub_user: User
):
    """stub_user cannot move an assignment that belongs to another user."""
    ctx = await _setup_project_and_workflow(db_session, stub_user)

    other = User(id=uuid.uuid4(), email="other3@test.com",
                 display_name="Other3", keycloak_id="other3-kc", is_active=True)
    db_session.add(other)
    await db_session.flush()

    from app.models.project import ProjectMember, ProjectMemberRole
    db_session.add(ProjectMember(
        project_id=uuid.UUID(ctx["project_id"]),
        user_id=other.id,
        role=ProjectMemberRole.member,
    ))
    await db_session.commit()

    r = await client.post(f"/api/v1/projects/{ctx['project_id']}/tasks", json={
        "title": "Other task", "workflow_id": ctx["workflow_id"],
    })
    task_id = r.json()["id"]

    from app.services import task_service as ts
    from app.schemas.task import AssignmentCreate
    a = await ts.assign_user(
        db_session, uuid.UUID(task_id),
        AssignmentCreate(user_id=other.id, role=AssigneeRole.lead), stub_user
    )

    r = await client.patch(f"/api/v1/assignments/{a.id}/status", json={
        "status_id": ctx["inprog_id"],
    })
    assert r.status_code == 403
    assert r.json()["detail"]["code"] == "PERMISSION_DENIED"


async def test_update_assignment_role(
    client: AsyncClient, db_session: AsyncSession, stub_user: User
):
    ctx = await _setup_project_and_workflow(db_session, stub_user)
    r = await client.post(f"/api/v1/projects/{ctx['project_id']}/tasks", json={
        "title": "Role test", "workflow_id": ctx["workflow_id"],
    })
    task_id = r.json()["id"]

    a = await client.post(f"/api/v1/tasks/{task_id}/assignments", json={
        "user_id": str(stub_user.id), "role": "lead",
    })
    assignment_id = a.json()["id"]

    # lead → reviewer: role changes and global_status recalculates (no leads left → open)
    r = await client.patch(f"/api/v1/assignments/{assignment_id}/role", json={"role": "reviewer"})
    assert r.status_code == 200
    assert r.json()["role"] == "reviewer"

    task = (await client.get(f"/api/v1/tasks/{task_id}")).json()
    assert task["global_status"] == "open"


async def test_remove_assignment_recalculates_to_open(
    client: AsyncClient, db_session: AsyncSession, stub_user: User
):
    """Removing the only lead assignment resets global_status to open."""
    ctx = await _setup_project_and_workflow(db_session, stub_user)
    r = await client.post(f"/api/v1/projects/{ctx['project_id']}/tasks", json={
        "title": "Remove test", "workflow_id": ctx["workflow_id"],
    })
    task_id = r.json()["id"]

    a = await client.post(f"/api/v1/tasks/{task_id}/assignments", json={
        "user_id": str(stub_user.id), "role": "lead",
    })
    assignment_id = a.json()["id"]

    task = (await client.get(f"/api/v1/tasks/{task_id}")).json()
    assert task["global_status"] == "in_progress"

    r = await client.delete(f"/api/v1/assignments/{assignment_id}")
    assert r.status_code == 204

    task = (await client.get(f"/api/v1/tasks/{task_id}")).json()
    assert task["global_status"] == "open"


async def test_my_tasks(
    client: AsyncClient, db_session: AsyncSession, stub_user: User
):
    ctx = await _setup_project_and_workflow(db_session, stub_user)
    r = await client.post(f"/api/v1/projects/{ctx['project_id']}/tasks", json={
        "title": "My Task", "workflow_id": ctx["workflow_id"],
    })
    task_id = r.json()["id"]
    await client.post(f"/api/v1/tasks/{task_id}/assignments", json={
        "user_id": str(stub_user.id), "role": "lead",
    })

    my = await client.get("/api/v1/users/me/tasks")
    assert my.status_code == 200
    assert any(t["id"] == task_id for t in my.json())


async def test_my_tasks_filters(
    client: AsyncClient, db_session: AsyncSession, stub_user: User
):
    ctx = await _setup_project_and_workflow(db_session, stub_user)

    # Reporter without assignment
    r1 = await client.post(f"/api/v1/projects/{ctx['project_id']}/tasks", json={
        "title": "T1 reporter only", "workflow_id": ctx["workflow_id"],
    })
    rep_id = r1.json()["id"]

    # Lead assignment
    r2 = await client.post(f"/api/v1/projects/{ctx['project_id']}/tasks", json={
        "title": "T2 assignee", "workflow_id": ctx["workflow_id"],
    })
    a2_id = r2.json()["id"]
    await client.post(f"/api/v1/tasks/{a2_id}/assignments", json={
        "user_id": str(stub_user.id), "role": "lead",
    })

    # DM only — assign reporter to be someone else via service
    other = User(id=uuid.uuid4(), email=f"dm-{uuid.uuid4().hex[:6]}@test.com",
                 display_name="Other", keycloak_id=str(uuid.uuid4()), is_active=True)
    db_session.add(other)
    await db_session.flush()
    from app.models.project import ProjectMember, ProjectMemberRole
    db_session.add(ProjectMember(
        project_id=uuid.UUID(ctx["project_id"]), user_id=other.id,
        role=ProjectMemberRole.member,
    ))
    await db_session.commit()

    from app.schemas.task import TaskCreate
    from app.services import task_service as ts
    dm_task = await ts.create_task(
        db_session, uuid.UUID(ctx["project_id"]),
        TaskCreate(
            title="T3 DM only", workflow_id=uuid.UUID(ctx["workflow_id"]),
            decision_maker_id=stub_user.id,
        ), other,
    )

    # Default — all three
    all_r = await client.get("/api/v1/users/me/tasks")
    ids = {t["id"] for t in all_r.json()}
    assert rep_id in ids and a2_id in ids and str(dm_task.id) in ids

    # role=reporter
    rep_r = await client.get("/api/v1/users/me/tasks?role=reporter")
    assert {t["id"] for t in rep_r.json()} >= {rep_id, a2_id}
    assert str(dm_task.id) not in {t["id"] for t in rep_r.json()}

    # role=assignee
    asg_r = await client.get("/api/v1/users/me/tasks?role=assignee")
    asg_ids = {t["id"] for t in asg_r.json()}
    assert a2_id in asg_ids
    assert rep_id not in asg_ids
    assert str(dm_task.id) not in asg_ids

    # role=dm
    dm_r = await client.get("/api/v1/users/me/tasks?role=dm")
    dm_ids = {t["id"] for t in dm_r.json()}
    assert dm_ids == {str(dm_task.id)}

    # global_status filter
    open_r = await client.get("/api/v1/users/me/tasks?global_status=open")
    assert all(t["global_status"] == "open" for t in open_r.json())
