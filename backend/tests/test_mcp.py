"""Tests for MCP tools: task, project, workflow operations.

McpSession opens its own DB connection; we patch it to inject the test
session and stub_user so the tools run against the isolated test transaction.
"""
import json
import uuid
from contextlib import asynccontextmanager
from unittest.mock import patch, MagicMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.schemas.project import ProjectCreate
from app.schemas.task import TaskCreate
from app.services import project_service, task_service


def _fake_ctx():
    """Minimal MCP Context stub (tools only inspect it inside McpSession)."""
    return MagicMock()


def _patch_session(db_session: AsyncSession, user: User):
    """Replaces McpSession in all tool modules with a stub that yields (db_session, user).

    Each tool module does `from app.mcp.utils import McpSession`, so we must patch
    the name in each module's namespace, not just in app.mcp.utils.
    """
    from contextlib import ExitStack

    class _FakeMcpSession:
        def __init__(self, ctx):
            pass
        async def __aenter__(self):
            return db_session, user
        async def __aexit__(self, *args):
            pass

    targets = [
        "app.mcp.tools.projects.McpSession",
        "app.mcp.tools.tasks.McpSession",
        "app.mcp.tools.workflows.McpSession",
    ]

    stack = ExitStack()
    for t in targets:
        stack.enter_context(patch(t, _FakeMcpSession))
    return stack


async def _setup(session: AsyncSession, user: User) -> dict:
    p = await project_service.create_project(
        session, ProjectCreate(name="MCP Test", key=uuid.uuid4().hex[:8].upper()), user
    )
    t = await task_service.create_task(
        session, p.id, TaskCreate(title="MCP Task"), user
    )
    return {"project_id": str(p.id), "task_id": str(t.id), "task_key": t.key}


# ── parse_uuid ────────────────────────────────────────────────────────────────

def test_parse_uuid_valid():
    from app.mcp.utils import parse_uuid
    uid = uuid.uuid4()
    assert parse_uuid(str(uid)) == uid


def test_parse_uuid_invalid():
    from mcp.shared.exceptions import McpError
    from app.mcp.utils import parse_uuid
    with pytest.raises(McpError):
        parse_uuid("not-a-uuid", "project_id")


# ── Project tools ─────────────────────────────────────────────────────────────

async def test_mcp_list_projects(db_session: AsyncSession, stub_user: User):
    from app.mcp.tools.projects import list_projects

    ctx = await _setup(db_session, stub_user)
    with _patch_session(db_session, stub_user):
        result = json.loads(await list_projects(_fake_ctx()))

    assert any(p["id"] == ctx["project_id"] for p in result)


async def test_mcp_get_project(db_session: AsyncSession, stub_user: User):
    from app.mcp.tools.projects import get_project

    ctx = await _setup(db_session, stub_user)
    with _patch_session(db_session, stub_user):
        result = json.loads(await get_project(_fake_ctx(), project_id=ctx["project_id"]))

    assert result["id"] == ctx["project_id"]
    assert "members" in result


async def test_mcp_get_project_invalid_uuid(db_session: AsyncSession, stub_user: User):
    from mcp.shared.exceptions import McpError
    from app.mcp.tools.projects import get_project

    with _patch_session(db_session, stub_user):
        with pytest.raises(McpError):
            await get_project(_fake_ctx(), project_id="bad-uuid")


# ── Task tools ────────────────────────────────────────────────────────────────

async def test_mcp_list_tasks(db_session: AsyncSession, stub_user: User):
    from app.mcp.tools.tasks import list_tasks

    ctx = await _setup(db_session, stub_user)
    with _patch_session(db_session, stub_user):
        result = json.loads(await list_tasks(_fake_ctx(), project_id=ctx["project_id"]))

    assert any(t["id"] == ctx["task_id"] for t in result)


async def test_mcp_list_tasks_filter_by_status(db_session: AsyncSession, stub_user: User):
    from app.mcp.tools.tasks import list_tasks

    ctx = await _setup(db_session, stub_user)
    with _patch_session(db_session, stub_user):
        result_todo = json.loads(await list_tasks(
            _fake_ctx(), project_id=ctx["project_id"], status_name="To Do"
        ))
        result_done = json.loads(await list_tasks(
            _fake_ctx(), project_id=ctx["project_id"], status_name="Done"
        ))

    assert any(t["id"] == ctx["task_id"] for t in result_todo)
    assert not any(t["id"] == ctx["task_id"] for t in result_done)


async def test_mcp_get_task(db_session: AsyncSession, stub_user: User):
    from app.mcp.tools.tasks import get_task

    ctx = await _setup(db_session, stub_user)
    with _patch_session(db_session, stub_user):
        result = json.loads(await get_task(_fake_ctx(), task_id=ctx["task_id"]))

    assert result["id"] == ctx["task_id"]
    assert result["title"] == "MCP Task"
    assert "current_status_name" in result
    assert "available_transitions" in result
    assert isinstance(result["available_transitions"], list)


async def test_mcp_get_task_by_key(db_session: AsyncSession, stub_user: User):
    from app.mcp.tools.tasks import get_task_by_key

    ctx = await _setup(db_session, stub_user)
    with _patch_session(db_session, stub_user):
        result = json.loads(await get_task_by_key(_fake_ctx(), key=ctx["task_key"]))

    assert result["id"] == ctx["task_id"]
    assert result["key"] == ctx["task_key"]


async def test_mcp_create_task(db_session: AsyncSession, stub_user: User):
    from app.mcp.tools.tasks import create_task

    ctx = await _setup(db_session, stub_user)
    with _patch_session(db_session, stub_user):
        result = json.loads(await create_task(
            _fake_ctx(),
            project_id=ctx["project_id"],
            title="Created via MCP",
            task_type_key="bug",
            priority="high",
        ))

    assert result["title"] == "Created via MCP"
    assert result["task_type_key"] == "bug"
    assert "current_status_name" in result


async def test_mcp_update_task(db_session: AsyncSession, stub_user: User):
    from app.mcp.tools.tasks import get_task, update_task

    ctx = await _setup(db_session, stub_user)
    with _patch_session(db_session, stub_user):
        before = json.loads(await get_task(_fake_ctx(), task_id=ctx["task_id"]))
        result = json.loads(await update_task(
            _fake_ctx(),
            task_id=ctx["task_id"],
            version=before["version"],
            title="Updated via MCP",
        ))

    assert result["title"] == "Updated via MCP"
    assert result["version"] == before["version"] + 1


async def test_mcp_update_task_version_conflict(db_session: AsyncSession, stub_user: User):
    from mcp.shared.exceptions import McpError
    from app.mcp.tools.tasks import update_task

    ctx = await _setup(db_session, stub_user)
    with _patch_session(db_session, stub_user):
        with pytest.raises(McpError) as exc_info:
            await update_task(
                _fake_ctx(), task_id=ctx["task_id"], version=999, title="Conflict",
            )
    assert "VERSION_CONFLICT" in str(exc_info.value)


async def test_mcp_list_my_tasks(db_session: AsyncSession, stub_user: User):
    from app.mcp.tools.tasks import list_my_tasks

    ctx = await _setup(db_session, stub_user)
    # Assign the task to stub_user
    t = await task_service.update_task(
        db_session,
        uuid.UUID(ctx["task_id"]),
        __import__("app.schemas.task", fromlist=["TaskUpdate"]).TaskUpdate(
            assignee_id=stub_user.id, version=1
        ),
        stub_user,
    )

    with _patch_session(db_session, stub_user):
        result = json.loads(await list_my_tasks(_fake_ctx(), role="assignee"))

    assert any(t["id"] == ctx["task_id"] for t in result)


async def test_mcp_transition_task_status(db_session: AsyncSession, stub_user: User):
    from sqlalchemy import select
    from app.mcp.tools.tasks import get_task, transition_task_status
    from app.schemas.task import TaskUpdate

    ctx = await _setup(db_session, stub_user)

    # Assign task to stub_user first (transition requires assignee)
    await task_service.update_task(
        db_session,
        uuid.UUID(ctx["task_id"]),
        TaskUpdate(assignee_id=stub_user.id, version=1),
        stub_user,
    )

    with _patch_session(db_session, stub_user):
        task_data = json.loads(await get_task(_fake_ctx(), task_id=ctx["task_id"]))
        transitions = task_data["available_transitions"]
        assert transitions, "No transitions available from initial status"

        target_status_id = transitions[0]["status_id"]
        result = json.loads(await transition_task_status(
            _fake_ctx(), task_id=ctx["task_id"], target_status_id=target_status_id
        ))

    assert result["current_status_id"] == target_status_id


# ── Workflow tools ────────────────────────────────────────────────────────────

async def test_mcp_list_workflows(db_session: AsyncSession, stub_user: User):
    from app.mcp.tools.workflows import list_workflows

    ctx = await _setup(db_session, stub_user)
    with _patch_session(db_session, stub_user):
        result = json.loads(await list_workflows(_fake_ctx(), project_id=ctx["project_id"]))

    assert len(result) >= 1
    wf = result[0]
    assert "statuses" in wf
    assert "transitions" in wf
    assert wf["is_default"] is True


async def test_mcp_get_workflow(db_session: AsyncSession, stub_user: User):
    from app.mcp.tools.workflows import list_workflows, get_workflow

    ctx = await _setup(db_session, stub_user)
    with _patch_session(db_session, stub_user):
        workflows = json.loads(await list_workflows(_fake_ctx(), project_id=ctx["project_id"]))
        wf_id = workflows[0]["id"]
        result = json.loads(await get_workflow(_fake_ctx(), workflow_id=wf_id))

    assert result["id"] == wf_id
    status_names = [s["name"] for s in result["statuses"]]
    assert "To Do" in status_names
