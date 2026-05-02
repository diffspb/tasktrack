import uuid

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.task import TaskPriority
from app.models.user import User
from app.schemas.project import ProjectCreate
from app.schemas.workflow import TransitionCreate
from app.services import project_service, workflow_service


def _rnd_key() -> str:
    return uuid.uuid4().hex[:8].upper()


async def _setup_project_and_workflow(session: AsyncSession, user: User) -> dict:
    """
    Creates project (which auto-creates a default workflow with standard statuses).
    Adds an In Progress → Done shortcut transition for tests.
    """
    from sqlalchemy import select
    from app.models.workflow import Workflow, Status, StatusCategory, Transition
    from app.models.resolution import Resolution

    project = await project_service.create_project(
        session, ProjectCreate(name="Task Test", key=_rnd_key()), user
    )

    # Use the auto-created default workflow
    wf = await session.scalar(
        select(Workflow).where(Workflow.project_id == project.id, Workflow.is_default == True)  # noqa: E712
    )
    statuses = list((await session.scalars(
        select(Status).where(Status.workflow_id == wf.id).order_by(Status.position)
    )).all())
    todo   = next(s for s in statuses if s.is_default)
    inprog = next(s for s in statuses if s.name == "In Progress")
    done   = next(s for s in statuses if s.category == StatusCategory.final)

    # Add shortcut In Progress → Done (auto-workflow has inprog→review→done)
    await workflow_service.create_transition(
        session, wf.id, TransitionCreate(from_status_id=inprog.id, to_status_id=done.id), user
    )

    resolution = await session.scalar(
        select(Resolution).where(Resolution.project_id == project.id, Resolution.is_default == True)  # noqa: E712
    )

    return {
        "project_id": str(project.id),
        "workflow_id": str(wf.id),
        "todo_id": str(todo.id),
        "inprog_id": str(inprog.id),
        "done_id": str(done.id),
        "resolution_id": str(resolution.id),
    }


# ─── Basic CRUD ────────────────────────────────────────────────────────────

async def test_create_task(client: AsyncClient, db_session: AsyncSession, stub_user: User):
    ctx = await _setup_project_and_workflow(db_session, stub_user)
    r = await client.post(f"/api/v1/projects/{ctx['project_id']}/tasks", json={
        "title": "My first task",
    })
    assert r.status_code == 201
    data = r.json()
    assert data["current_status_id"] == ctx["todo_id"]
    assert data["assignee_id"] is None
    assert data["parent_task_id"] is None
    assert data["version"] == 1
    assert data["task_type"]["key"] == "task"


async def test_create_task_with_explicit_type(
    client: AsyncClient, db_session: AsyncSession, stub_user: User
):
    ctx = await _setup_project_and_workflow(db_session, stub_user)
    r = await client.post(f"/api/v1/projects/{ctx['project_id']}/tasks", json={
        "title": "A bug", "task_type_key": "bug",
    })
    assert r.status_code == 201
    assert r.json()["task_type"]["key"] == "bug"


async def test_create_task_unknown_type(
    client: AsyncClient, db_session: AsyncSession, stub_user: User
):
    ctx = await _setup_project_and_workflow(db_session, stub_user)
    r = await client.post(f"/api/v1/projects/{ctx['project_id']}/tasks", json={
        "title": "T", "task_type_key": "nonexistent",
    })
    assert r.status_code == 400
    assert r.json()["detail"]["code"] == "TASK_TYPE_NOT_FOUND"


async def test_task_key_autoincrement(
    client: AsyncClient, db_session: AsyncSession, stub_user: User
):
    ctx = await _setup_project_and_workflow(db_session, stub_user)
    pid = ctx["project_id"]
    r1 = await client.post(f"/api/v1/projects/{pid}/tasks", json={"title": "T1"})
    r2 = await client.post(f"/api/v1/projects/{pid}/tasks", json={"title": "T2"})
    num1 = int(r1.json()["key"].split("-")[-1])
    num2 = int(r2.json()["key"].split("-")[-1])
    assert num2 == num1 + 1


async def test_get_task_by_key(
    client: AsyncClient, db_session: AsyncSession, stub_user: User
):
    ctx = await _setup_project_and_workflow(db_session, stub_user)
    r = await client.post(f"/api/v1/projects/{ctx['project_id']}/tasks", json={"title": "ByKey"})
    key = r.json()["key"]

    r2 = await client.get(f"/api/v1/tasks/by-key/{key}")
    assert r2.status_code == 200
    assert r2.json()["key"] == key


async def test_create_task_default_workflow(
    client: AsyncClient, db_session: AsyncSession, stub_user: User
):
    """Task creation without explicit workflow_id uses project's default workflow."""
    ctx = await _setup_project_and_workflow(db_session, stub_user)
    r = await client.post(f"/api/v1/projects/{ctx['project_id']}/tasks", json={"title": "Auto-wf"})
    assert r.status_code == 201
    assert r.json()["workflow_id"] == ctx["workflow_id"]
    assert r.json()["current_status_id"] == ctx["todo_id"]


# ─── Assignee & status transition ────────────────────────────────────────────

async def test_create_task_with_assignee(
    client: AsyncClient, db_session: AsyncSession, stub_user: User
):
    ctx = await _setup_project_and_workflow(db_session, stub_user)
    r = await client.post(f"/api/v1/projects/{ctx['project_id']}/tasks", json={
        "title": "Assigned", "assignee_id": str(stub_user.id),
    })
    assert r.status_code == 201
    assert r.json()["assignee_id"] == str(stub_user.id)


async def test_full_workflow(
    client: AsyncClient, db_session: AsyncSession, stub_user: User
):
    """create → assign via update → To Do → In Progress → Done."""
    ctx = await _setup_project_and_workflow(db_session, stub_user)

    r = await client.post(f"/api/v1/projects/{ctx['project_id']}/tasks", json={"title": "Full flow"})
    data = r.json()
    task_id = data["id"]
    assert data["current_status_id"] == ctx["todo_id"]

    # Assign via PATCH
    up = await client.patch(f"/api/v1/tasks/{task_id}", json={
        "assignee_id": str(stub_user.id), "version": 1,
    })
    assert up.status_code == 200
    assert up.json()["assignee_id"] == str(stub_user.id)

    # To Do → In Progress
    t1 = await client.post(f"/api/v1/tasks/{task_id}/transition", json={
        "status_id": ctx["inprog_id"],
    })
    assert t1.status_code == 200
    assert t1.json()["current_status_id"] == ctx["inprog_id"]

    # In Progress → Done (requires resolution)
    t2 = await client.post(f"/api/v1/tasks/{task_id}/transition", json={
        "status_id": ctx["done_id"],
        "resolution_id": ctx["resolution_id"],
    })
    assert t2.status_code == 200
    assert t2.json()["current_status_id"] == ctx["done_id"]


async def test_transition_not_allowed(
    client: AsyncClient, db_session: AsyncSession, stub_user: User
):
    ctx = await _setup_project_and_workflow(db_session, stub_user)
    r = await client.post(f"/api/v1/projects/{ctx['project_id']}/tasks", json={
        "title": "T", "assignee_id": str(stub_user.id),
    })
    task_id = r.json()["id"]

    # Find Review status (no direct transition from To Do → Review)
    from sqlalchemy import select
    from app.models.workflow import Status, StatusCategory
    review = await db_session.scalar(
        select(Status).where(
            Status.workflow_id == uuid.UUID(ctx["workflow_id"]),
            Status.name == "Review",
        )
    )
    r = await client.post(f"/api/v1/tasks/{task_id}/transition", json={
        "status_id": str(review.id),
    })
    assert r.status_code == 400
    assert r.json()["detail"]["code"] == "WORKFLOW_TRANSITION_NOT_ALLOWED"


async def test_resolution_required(
    client: AsyncClient, db_session: AsyncSession, stub_user: User
):
    ctx = await _setup_project_and_workflow(db_session, stub_user)
    r = await client.post(f"/api/v1/projects/{ctx['project_id']}/tasks", json={
        "title": "T", "assignee_id": str(stub_user.id),
    })
    task_id = r.json()["id"]
    await client.post(f"/api/v1/tasks/{task_id}/transition", json={"status_id": ctx["inprog_id"]})

    r = await client.post(f"/api/v1/tasks/{task_id}/transition", json={
        "status_id": ctx["done_id"],  # no resolution_id
    })
    assert r.status_code == 400
    assert r.json()["detail"]["code"] == "RESOLUTION_REQUIRED"


async def test_transition_forbidden_for_non_assignee(
    client: AsyncClient, db_session: AsyncSession, stub_user: User
):
    """stub_user cannot transition a task assigned to someone else."""
    ctx = await _setup_project_and_workflow(db_session, stub_user)

    other = User(id=uuid.uuid4(), email="other@t.com", display_name="O",
                 keycloak_id=str(uuid.uuid4()), is_active=True)
    db_session.add(other)
    await db_session.flush()
    from app.models.project import ProjectMember, ProjectMemberRole
    db_session.add(ProjectMember(
        project_id=uuid.UUID(ctx["project_id"]),
        user_id=other.id, role=ProjectMemberRole.member,
    ))
    await db_session.flush()

    r = await client.post(f"/api/v1/projects/{ctx['project_id']}/tasks", json={
        "title": "Other's task", "assignee_id": str(other.id),
    })
    task_id = r.json()["id"]

    r = await client.post(f"/api/v1/tasks/{task_id}/transition", json={
        "status_id": ctx["inprog_id"],
    })
    assert r.status_code == 403
    assert r.json()["detail"]["code"] == "PERMISSION_DENIED"


# ─── Subtasks / Decision ─────────────────────────────────────────────────────

async def test_create_subtask(
    client: AsyncClient, db_session: AsyncSession, stub_user: User
):
    ctx = await _setup_project_and_workflow(db_session, stub_user)
    parent = await client.post(f"/api/v1/projects/{ctx['project_id']}/tasks", json={
        "title": "Parent", "task_type_key": "decision",
    })
    parent_id = parent.json()["id"]

    child = await client.post(f"/api/v1/projects/{ctx['project_id']}/tasks", json={
        "title": "Child", "parent_task_id": parent_id,
    })
    assert child.status_code == 201
    assert child.json()["parent_task_id"] == parent_id


async def test_decision_task_blocked_until_subtasks_ready(
    client: AsyncClient, db_session: AsyncSession, stub_user: User
):
    """Decision task transition is blocked if subtasks lack solution_comment_id."""
    ctx = await _setup_project_and_workflow(db_session, stub_user)

    parent = await client.post(f"/api/v1/projects/{ctx['project_id']}/tasks", json={
        "title": "Decision", "task_type_key": "decision",
        "assignee_id": str(stub_user.id),
    })
    parent_id = parent.json()["id"]

    # Add a subtask without solution comment
    await client.post(f"/api/v1/projects/{ctx['project_id']}/tasks", json={
        "title": "Sub", "parent_task_id": parent_id,
    })

    r = await client.post(f"/api/v1/tasks/{parent_id}/transition", json={
        "status_id": ctx["inprog_id"],
    })
    assert r.status_code == 400
    assert r.json()["detail"]["code"] == "TASK_BLOCKED_BY_SUBTASKS"


# ─── PATCH, delete, version conflict ─────────────────────────────────────────

async def test_soft_delete_task(
    client: AsyncClient, db_session: AsyncSession, stub_user: User
):
    ctx = await _setup_project_and_workflow(db_session, stub_user)
    r = await client.post(f"/api/v1/projects/{ctx['project_id']}/tasks", json={"title": "To delete"})
    task_id = r.json()["id"]

    assert (await client.delete(f"/api/v1/tasks/{task_id}")).status_code == 204
    assert (await client.get(f"/api/v1/tasks/{task_id}")).status_code == 404


async def test_version_conflict(
    client: AsyncClient, db_session: AsyncSession, stub_user: User
):
    ctx = await _setup_project_and_workflow(db_session, stub_user)
    r = await client.post(f"/api/v1/projects/{ctx['project_id']}/tasks", json={"title": "Versioned"})
    task_id = r.json()["id"]

    r = await client.patch(f"/api/v1/tasks/{task_id}", json={"title": "Updated", "version": 99})
    assert r.status_code == 409
    assert r.json()["detail"]["code"] == "VERSION_CONFLICT"


async def test_update_task_meta(
    client: AsyncClient, db_session: AsyncSession, stub_user: User
):
    ctx = await _setup_project_and_workflow(db_session, stub_user)
    r = await client.post(f"/api/v1/projects/{ctx['project_id']}/tasks", json={"title": "Meta"})
    task_id, version = r.json()["id"], r.json()["version"]

    up = await client.patch(f"/api/v1/tasks/{task_id}", json={
        "meta": {"foo": "bar"}, "version": version,
    })
    assert up.status_code == 200
    assert up.json()["meta"]["foo"] == "bar"


# ─── List & dashboard ────────────────────────────────────────────────────────

async def test_list_tasks_filter_by_assignee(
    client: AsyncClient, db_session: AsyncSession, stub_user: User
):
    ctx = await _setup_project_and_workflow(db_session, stub_user)
    pid = ctx["project_id"]

    await client.post(f"/api/v1/projects/{pid}/tasks", json={"title": "Unassigned"})
    await client.post(f"/api/v1/projects/{pid}/tasks", json={
        "title": "Mine", "assignee_id": str(stub_user.id),
    })

    r = await client.get(f"/api/v1/projects/{pid}/tasks?assignee_id={stub_user.id}")
    assert all(t["assignee_id"] == str(stub_user.id) for t in r.json())
    assert len(r.json()) >= 1


async def test_my_tasks(
    client: AsyncClient, db_session: AsyncSession, stub_user: User
):
    ctx = await _setup_project_and_workflow(db_session, stub_user)
    r = await client.post(f"/api/v1/projects/{ctx['project_id']}/tasks", json={
        "title": "My Task", "assignee_id": str(stub_user.id),
    })
    task_id = r.json()["id"]

    my = await client.get("/api/v1/users/me/tasks")
    assert my.status_code == 200
    assert any(t["id"] == task_id for t in my.json())


async def test_my_tasks_role_filter(
    client: AsyncClient, db_session: AsyncSession, stub_user: User
):
    ctx = await _setup_project_and_workflow(db_session, stub_user)

    # Reporter task (reported by stub_user, assigned to nobody)
    r1 = await client.post(f"/api/v1/projects/{ctx['project_id']}/tasks", json={"title": "Reporter"})
    rep_id = r1.json()["id"]

    # Assignee task
    r2 = await client.post(f"/api/v1/projects/{ctx['project_id']}/tasks", json={
        "title": "Assignee", "assignee_id": str(stub_user.id),
    })
    asg_id = r2.json()["id"]

    asg_r = await client.get("/api/v1/users/me/tasks?role=assignee")
    asg_ids = {t["id"] for t in asg_r.json()}
    assert asg_id in asg_ids
    assert rep_id not in asg_ids

    rep_r = await client.get("/api/v1/users/me/tasks?role=reporter")
    rep_ids = {t["id"] for t in rep_r.json()}
    assert rep_id in rep_ids


# ─── P2 error paths ──────────────────────────────────────────────────────────

async def test_get_task_not_found(client: AsyncClient):
    r = await client.get(f"/api/v1/tasks/{uuid.uuid4()}")
    assert r.status_code == 404
    assert r.json()["detail"]["code"] == "TASK_NOT_FOUND"


async def test_patch_task_not_found(client: AsyncClient):
    r = await client.patch(f"/api/v1/tasks/{uuid.uuid4()}", json={"title": "X", "version": 1})
    assert r.status_code == 404
    assert r.json()["detail"]["code"] == "TASK_NOT_FOUND"


async def test_delete_task_not_found(client: AsyncClient):
    r = await client.delete(f"/api/v1/tasks/{uuid.uuid4()}")
    assert r.status_code == 404
    assert r.json()["detail"]["code"] == "TASK_NOT_FOUND"


async def test_transition_task_not_found(client: AsyncClient):
    r = await client.post(f"/api/v1/tasks/{uuid.uuid4()}/transition",
                          json={"status_id": str(uuid.uuid4())})
    assert r.status_code == 404
    assert r.json()["detail"]["code"] == "TASK_NOT_FOUND"


async def test_no_default_status_explicit_workflow(
    client: AsyncClient, db_session: AsyncSession, stub_user: User
):
    """Explicit workflow_id with no default status raises WORKFLOW_NO_DEFAULT_STATUS."""
    from sqlalchemy import select
    from app.models.workflow import Workflow, Status
    from app.schemas.workflow import WorkflowCreate

    ctx = await _setup_project_and_workflow(db_session, stub_user)

    # Create a second workflow (no default status) and pass it explicitly
    wf2 = await workflow_service.create_workflow(
        db_session, uuid.UUID(ctx["project_id"]), WorkflowCreate(name="Empty WF"), stub_user
    )
    r = await client.post(f"/api/v1/projects/{ctx['project_id']}/tasks", json={
        "title": "T", "workflow_id": str(wf2.id),
    })
    assert r.status_code == 400
    assert r.json()["detail"]["code"] == "WORKFLOW_NO_DEFAULT_STATUS"
