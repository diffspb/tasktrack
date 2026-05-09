import json
import uuid as _uuid

from mcp.server.fastmcp.server import Context
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from app.mcp.schemas.task import task_detail, task_list_item
from app.mcp.utils import McpSession, parse_uuid, svc_call
from app.models.task import Task
from app.models.workflow import Status, Transition, Workflow
from app.schemas.task import TaskCreate, TaskStatusTransition, TaskUpdate
from app.services import task_link_service, task_service


# --- helpers ---

async def _enrich_task(session, task: Task, user=None) -> dict:
    """Load status, transitions, links and return full MCP task dict."""
    status = await session.get(Status, task.current_status_id)
    transitions = list((await session.scalars(
        select(Transition)
        .where(Transition.from_status_id == task.current_status_id)
        .options(selectinload(Transition.to_status))
    )).all())
    links = await task_link_service.get_task_links(session, task.id, user) if user else []
    return task_detail(task, status, transitions, links)


async def _resolve_status_id(
    session, project_id: _uuid.UUID, status_name: str
) -> _uuid.UUID | None:
    """Resolve a human-readable status name to a status_id within a project."""
    wf_ids = list((await session.scalars(
        select(Workflow.id).where(Workflow.project_id == project_id)
    )).all())
    if not wf_ids:
        return None
    status = await session.scalar(
        select(Status).where(
            Status.workflow_id.in_(wf_ids),
            func.lower(Status.name) == status_name.lower(),
        )
    )
    return status.id if status else None


async def _enrich_list(session, tasks: list[Task]) -> list[dict]:
    if not tasks:
        return []
    status_ids = {t.current_status_id for t in tasks}
    statuses = {
        s.id: s
        for s in (await session.scalars(
            select(Status).where(Status.id.in_(status_ids))
        )).all()
    }
    return [task_list_item(t, statuses.get(t.current_status_id)) for t in tasks]


# --- tools ---

@svc_call
async def list_tasks(
    ctx: Context,
    project_id: str,
    status_name: str | None = None,
    assignee_id: str | None = None,
    task_type_key: str | None = None,
    parent_task_id: str | None = None,
    top_level_only: bool = False,
) -> str:
    """
    List tasks in a project with optional filters.

    status_name: filter by status name, case-insensitive (e.g. "In Progress").
    assignee_id: UUID of the assignee.
    task_type_key: "task" | "bug" | "story" | "epic" | "decision".
    parent_task_id: UUID — list only direct subtasks of this task.
    top_level_only: if true, exclude all subtasks.

    Each item: id, key, title, priority, task_type_key, current_status_id,
    current_status_name, current_status_category, assignee_id, parent_task_id,
    due_date, version.
    """
    async with McpSession(ctx) as (session, user):
        pid = parse_uuid(project_id, "project_id")
        aid = parse_uuid(assignee_id, "assignee_id") if assignee_id else None
        par = parse_uuid(parent_task_id, "parent_task_id") if parent_task_id else None

        resolved_status_id = None
        if status_name:
            resolved_status_id = await _resolve_status_id(session, pid, status_name)

        tasks = await task_service.list_tasks(
            session, pid, user,
            status_id=resolved_status_id,
            assignee_id=aid,
            task_type_key=task_type_key,
            parent_task_id=par,
            include_subtasks=not top_level_only,
        )
        return json.dumps(await _enrich_list(session, tasks))


@svc_call
async def get_task(ctx: Context, task_id: str) -> str:
    """
    Get complete task details by UUID.

    Returns all fields plus:
    - current_status_name / current_status_category
    - available_transitions: [{status_id, status_name, status_category}]
    - subtask_count, subtask_ids
    - is_decision_task: true if task_type_key == "decision"

    Always call get_task before update_task to get the current version.
    """
    async with McpSession(ctx) as (session, user):
        tid = parse_uuid(task_id, "task_id")
        task = await task_service.get_task(session, tid, user)
        return json.dumps(await _enrich_task(session, task, user))


@svc_call
async def get_task_by_key(ctx: Context, key: str) -> str:
    """
    Get complete task details by task key (e.g. "DEMO-10").

    Returns the same enriched response as get_task.
    Use this when you know the human-readable key rather than the UUID.
    """
    async with McpSession(ctx) as (session, user):
        task = await task_service.get_task_by_key(session, key.upper(), user)
        return json.dumps(await _enrich_task(session, task, user))


@svc_call
async def list_my_tasks(
    ctx: Context,
    role: str | None = None,
    status_name: str | None = None,
    project_id: str | None = None,
) -> str:
    """
    List tasks assigned to or reported by the agent's own user.

    role: "assignee" | "reporter" | null (both).
    status_name: filter by status name, case-insensitive.
    project_id: filter to a specific project.

    Returns the same per-item fields as list_tasks.
    """
    async with McpSession(ctx) as (session, user):
        pid = parse_uuid(project_id, "project_id") if project_id else None

        resolved_status_id = None
        if status_name and pid:
            resolved_status_id = await _resolve_status_id(session, pid, status_name)

        tasks = await task_service.list_my_tasks(
            session, user,
            role=role,
            status_id=resolved_status_id,
            project_id=pid,
        )
        return json.dumps(await _enrich_list(session, tasks))


@svc_call
async def create_task(
    ctx: Context,
    project_id: str,
    title: str,
    task_type_key: str = "task",
    description: str | None = None,
    priority: str = "medium",
    assignee_id: str | None = None,
    parent_task_id: str | None = None,
    due_date: str | None = None,
) -> str:
    """
    Create a new task in the specified project.

    task_type_key: "task" | "bug" | "story" | "epic" | "decision"
    priority: "low" | "medium" | "high" | "critical"
    due_date: ISO date string, e.g. "2026-06-01"

    The workflow and initial status are assigned automatically based on
    project task-type configuration. The agent is set as reporter.

    Returns the full enriched task response.
    """
    from datetime import date
    async with McpSession(ctx) as (session, user):
        pid = parse_uuid(project_id, "project_id")
        aid = parse_uuid(assignee_id, "assignee_id") if assignee_id else None
        par = parse_uuid(parent_task_id, "parent_task_id") if parent_task_id else None
        dd = date.fromisoformat(due_date) if due_date else None

        data = TaskCreate(
            title=title,
            task_type_key=task_type_key,
            description=description,
            priority=priority,
            assignee_id=aid,
            parent_task_id=par,
            due_date=dd,
        )
        task = await task_service.create_task(session, pid, data, user)
        return json.dumps(await _enrich_task(session, task, user))


@svc_call
async def update_task(
    ctx: Context,
    task_id: str,
    version: int,
    title: str | None = None,
    description: str | None = None,
    priority: str | None = None,
    assignee_id: str | None = None,
    start_date: str | None = None,
    due_date: str | None = None,
) -> str:
    """
    Update mutable fields of a task.

    IMPORTANT: version is required for optimistic locking. Always read the
    current task with get_task first and pass back the version you received.
    If another process updated the task concurrently, this returns VERSION_CONFLICT
    — re-read and retry.

    Only provide fields you want to change; omit others (pass null).
    start_date / due_date: ISO date string, e.g. "2026-06-01". Pass null to clear.
    Returns the updated task with the incremented version.
    """
    from datetime import date
    async with McpSession(ctx) as (session, user):
        tid = parse_uuid(task_id, "task_id")
        aid = parse_uuid(assignee_id, "assignee_id") if assignee_id else None
        sd = date.fromisoformat(start_date) if start_date else None
        dd = date.fromisoformat(due_date) if due_date else None

        data = TaskUpdate(
            version=version,
            title=title,
            description=description,
            priority=priority,
            assignee_id=aid,
            start_date=sd,
            due_date=dd,
        )
        task = await task_service.update_task(session, tid, data, user)
        return json.dumps(await _enrich_task(session, task, user))


@svc_call
async def transition_task_status(
    ctx: Context,
    task_id: str,
    target_status_id: str,
) -> str:
    """
    Move a task to a different status following workflow transition rules.

    The agent must be the task's assignee to perform a transition.
    Only transitions listed in get_task.available_transitions are allowed.

    For decision tasks: transitioning to final is blocked if any subtask
    lacks a solution comment (check is_decision_task and subtask_ids first).

    Returns the updated task.
    """
    async with McpSession(ctx) as (session, user):
        tid = parse_uuid(task_id, "task_id")
        sid = parse_uuid(target_status_id, "target_status_id")

        data = TaskStatusTransition(status_id=sid)
        task = await task_service.transition_status(session, tid, data, user)
        return json.dumps(await _enrich_task(session, task, user))
