"""Tests for workflow selection by task type and task-type-configs API."""
import uuid

from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.task_type import TaskType
from app.models.user import User
from app.models.workflow import ProjectTaskTypeConfig, Status, StatusCategory, Workflow
from app.schemas.project import ProjectCreate
from app.schemas.workflow import TransitionCreate, WorkflowCreate
from app.services import project_service, workflow_service


async def _make_project(session: AsyncSession, user: User) -> str:
    """Creates a project with default workflow (via project_service)."""
    p = await project_service.create_project(
        session, ProjectCreate(name="WF Test", key=uuid.uuid4().hex[:8].upper()), user
    )
    return str(p.id)


async def test_create_task_uses_project_default_workflow(
    client: AsyncClient, db_session: AsyncSession, stub_user: User
):
    """Task is created → uses project's is_default workflow (backward compat)."""
    pid = await _make_project(db_session, stub_user)
    r = await client.post(f"/api/v1/projects/{pid}/tasks", json={"title": "T"})
    assert r.status_code == 201
    task = r.json()
    # workflow must be the project default
    wf_r = await client.get(f"/api/v1/projects/{pid}/workflows")
    project_wf = wf_r.json()[0]
    assert task["workflow_id"] == project_wf["id"]


async def test_create_task_no_project_default_raises(
    client: AsyncClient, db_session: AsyncSession, stub_user: User
):
    """No ProjectTaskTypeConfig, no project default workflow → 400 NO_DEFAULT_WORKFLOW.

    System workflow fallback (via TaskType.default_workflow_id) is intentionally NOT used:
    system workflows are invisible to the board's useProjectWorkflows query and would cause
    tasks to appear without a visible status. Explicit ProjectTaskTypeConfig is required.
    """
    from app.models.project import Project, ProjectMember, ProjectMemberRole, ProjectVisibility
    project = Project(
        name="No Default WF",
        key=uuid.uuid4().hex[:8].upper(),
        visibility=ProjectVisibility.restricted,
        owner_id=stub_user.id,
    )
    db_session.add(project)
    await db_session.flush()
    db_session.add(ProjectMember(project_id=project.id, user_id=stub_user.id, role=ProjectMemberRole.admin))
    await db_session.flush()

    r = await client.post(f"/api/v1/projects/{project.id}/tasks", json={"title": "No WF Task"})
    assert r.status_code == 400
    assert r.json()["detail"]["code"] == "NO_DEFAULT_WORKFLOW"


async def test_create_task_uses_project_override(
    client: AsyncClient, db_session: AsyncSession, stub_user: User
):
    """ProjectTaskTypeConfig overrides system default → task uses configured workflow."""
    pid = await _make_project(db_session, stub_user)
    project_uuid = uuid.UUID(pid)

    # Create a second workflow for the project
    wf2 = await workflow_service.create_workflow(
        db_session, project_uuid, WorkflowCreate(name="Bug WF"), stub_user
    )
    s = Status(workflow_id=wf2.id, name="Open", category=StatusCategory.initial, is_default=True, position=0)
    db_session.add(s)
    await db_session.flush()

    # Set override for 'bug' task type
    tt = await db_session.scalar(
        select(TaskType).where(TaskType.key == "bug", TaskType.is_system.is_(True))
    )
    r = await client.put(
        f"/api/v1/projects/{pid}/task-type-configs/{tt.id}",
        json={"workflow_id": str(wf2.id)},
    )
    assert r.status_code == 200

    # Create bug task — should use wf2
    bug_r = await client.post(f"/api/v1/projects/{pid}/tasks", json={
        "title": "Bug task",
        "task_type_key": "bug",
    })
    assert bug_r.status_code == 201
    assert bug_r.json()["workflow_id"] == str(wf2.id)



async def test_set_task_type_workflow_upsert(
    client: AsyncClient, db_session: AsyncSession, stub_user: User
):
    """PUT creates config; second PUT updates workflow_id."""
    pid = await _make_project(db_session, stub_user)
    project_uuid = uuid.UUID(pid)

    wf2 = await workflow_service.create_workflow(
        db_session, project_uuid, WorkflowCreate(name="WF2"), stub_user
    )
    wf3 = await workflow_service.create_workflow(
        db_session, project_uuid, WorkflowCreate(name="WF3"), stub_user
    )

    tt = await db_session.scalar(
        select(TaskType).where(TaskType.key == "bug", TaskType.is_system.is_(True))
    )
    # First PUT — create
    r1 = await client.put(
        f"/api/v1/projects/{pid}/task-type-configs/{tt.id}",
        json={"workflow_id": str(wf2.id)},
    )
    assert r1.status_code == 200

    # Verify via GET
    cfg_r = await client.get(f"/api/v1/projects/{pid}/task-type-configs")
    configs = cfg_r.json()["items"]
    bug_cfg = next(c for c in configs if c["task_type_key"] == "bug")
    assert bug_cfg["workflow_id"] == str(wf2.id)
    assert bug_cfg["is_project_override"] is True

    # Second PUT — update
    r2 = await client.put(
        f"/api/v1/projects/{pid}/task-type-configs/{tt.id}",
        json={"workflow_id": str(wf3.id)},
    )
    assert r2.status_code == 200

    cfg_r2 = await client.get(f"/api/v1/projects/{pid}/task-type-configs")
    bug_cfg2 = next(c for c in cfg_r2.json()["items"] if c["task_type_key"] == "bug")
    assert bug_cfg2["workflow_id"] == str(wf3.id)


async def test_set_task_type_workflow_not_accessible(
    client: AsyncClient, db_session: AsyncSession, stub_user: User
):
    """Workflow from another project → 400 WORKFLOW_NOT_ACCESSIBLE."""
    pid1 = await _make_project(db_session, stub_user)
    pid2 = await _make_project(db_session, stub_user)

    # Get project 2's default workflow
    wf_r = await client.get(f"/api/v1/projects/{pid2}/workflows")
    wf2_id = wf_r.json()[0]["id"]

    tt = await db_session.scalar(
        select(TaskType).where(TaskType.key == "bug", TaskType.is_system.is_(True))
    )
    r = await client.put(
        f"/api/v1/projects/{pid1}/task-type-configs/{tt.id}",
        json={"workflow_id": wf2_id},
    )
    assert r.status_code == 400
    assert r.json()["detail"]["code"] == "WORKFLOW_NOT_ACCESSIBLE"


async def test_reset_task_type_workflow(
    client: AsyncClient, db_session: AsyncSession, stub_user: User
):
    """DELETE config → task falls back to system default (or project default)."""
    pid = await _make_project(db_session, stub_user)
    project_uuid = uuid.UUID(pid)

    wf2 = await workflow_service.create_workflow(
        db_session, project_uuid, WorkflowCreate(name="Override WF"), stub_user
    )

    tt = await db_session.scalar(
        select(TaskType).where(TaskType.key == "story", TaskType.is_system.is_(True))
    )
    # Set override
    await client.put(
        f"/api/v1/projects/{pid}/task-type-configs/{tt.id}",
        json={"workflow_id": str(wf2.id)},
    )

    # Reset
    del_r = await client.delete(f"/api/v1/projects/{pid}/task-type-configs/{tt.id}")
    assert del_r.status_code == 204

    # Config should be gone
    cfg_r = await client.get(f"/api/v1/projects/{pid}/task-type-configs")
    story_cfg = next(c for c in cfg_r.json()["items"] if c["task_type_key"] == "story")
    assert story_cfg["is_project_override"] is False
    assert story_cfg["workflow_id"] != str(wf2.id)
