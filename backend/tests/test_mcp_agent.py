"""Агентский контракт через MCP (FR-003, TT-18).

Инструменты вызываются через настоящий McpSession: аутентификация, сессия
исполнения, причина и повтор по ключу работают так же, как в REST.
"""
import json
import uuid
from contextlib import contextmanager
from unittest.mock import MagicMock, patch

import pytest
from mcp.shared.exceptions import McpError
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.mcp.tools import work
from app.mcp.tools.comments import add_comment
from app.models.project import ProjectMember, ProjectMemberRole
from app.models.result import ResultProposal
from app.models.user import User
from app.schemas.project import ProjectCreate
from app.schemas.task import TaskCreate
from app.schemas.work_package import WorkPackageContent
from app.services import project_service, task_service, work_package_service


class _SessionFactory:
    def __init__(self, session: AsyncSession):
        self._session = session

    def __call__(self):
        return self

    async def __aenter__(self):
        return self._session

    async def __aexit__(self, *args):
        pass


@contextmanager
def as_agent(db_session: AsyncSession, user: User):
    with patch("app.mcp.utils.SessionLocal", _SessionFactory(db_session)), \
         patch("app.mcp.utils.get_user_for_key", lambda key: user):
        yield


def _ctx():
    ctx = MagicMock()
    ctx.request_context.request.headers = {}
    return ctx


async def _world(db_session: AsyncSession, owner: User) -> dict:
    project = await project_service.create_project(
        db_session, ProjectCreate(name="MCP", key=uuid.uuid4().hex[:8].upper()), owner
    )
    agent = User(id=uuid.uuid4(), email=f"agent_{uuid.uuid4().hex[:6]}@agents", display_name="Agent",
                 keycloak_id=f"service:{uuid.uuid4()}", is_active=True, is_service=True)
    reviewer = User(id=uuid.uuid4(), email=f"rev_{uuid.uuid4().hex[:6]}@t.com", display_name="Rev",
                    keycloak_id=str(uuid.uuid4()), is_active=True)
    db_session.add_all([agent, reviewer])
    await db_session.flush()
    db_session.add_all([
        ProjectMember(project_id=project.id, user_id=agent.id, role=ProjectMemberRole.member),
        ProjectMember(project_id=project.id, user_id=reviewer.id, role=ProjectMemberRole.member, is_reviewer=True),
    ])
    await db_session.flush()
    task = await task_service.create_task(
        db_session, project.id, TaskCreate(title="Сделать отчёт", assignee_id=agent.id), owner
    )
    await work_package_service.save_draft(db_session, task.id, WorkPackageContent(
        goal="Отчёт", expected_result="PDF", criteria=[{"text": "Разделы на месте"}], specialization="analytics",
    ), owner)
    await work_package_service.issue(db_session, task.id, owner)
    return {"task": task, "agent": agent, "reviewer": reviewer}


async def test_full_agent_cycle(db_session: AsyncSession, stub_user: User):
    w = await _world(db_session, stub_user)
    tid = str(w["task"].id)
    ctx = _ctx()

    with as_agent(db_session, w["agent"]):
        package = json.loads(await work.get_work_package(ctx, tid))
        assert package["version"] == 1 and package["content"]["criteria"][0]["key"] == "c1"

        s = json.loads(await work.claim_task(ctx, tid, machine="gpu-1", client="claude-code"))
        assert s["work_package_id"] == package["id"]
        with pytest.raises(McpError, match="SESSION_ACTIVE"):
            await work.claim_task(ctx, tid, machine="laptop")

        await work.checkpoint(ctx, s["id"], "данные собраны", {"rows": 120})
        await add_comment(ctx, tid, "черновик готов", session_id=s["id"])
        p = json.loads(await work.submit_result(
            ctx, tid, "Отчёт готов",
            links=[{"kind": "document", "url": "https://files/report.pdf"}],
            criteria=[{"key": "c1", "status": "met"}],
            session_id=s["id"], reason="завершено по заданию",
        ))
        assert p["session_id"] == s["id"] and p["work_package_id"] == package["id"]
        await work.finish_session(ctx, s["id"], "подано")

    with as_agent(db_session, w["reviewer"]):
        queue = json.loads(await work.list_review_queue(ctx))
        assert [q["id"] for q in queue] == [p["id"]]
        r = json.loads(await work.review_result(
            ctx, p["id"], "accepted", "Все разделы на месте", criteria=[{"key": "c1", "verdict": "met"}],
        ))
        assert r["verdict"] == "accepted"
        assert json.loads(await work.list_review_queue(ctx)) == []

        history = json.loads(await work.get_task_history(ctx, tid))["items"]
        kinds = [(e["entity_type"], e["action"]) for e in history]
        assert ("task_session", "started") in kinds and ("review", "created") in kinds
        proposal_event = next(e for e in history if e["entity_type"] == "result_proposal")
        assert proposal_event["session_id"] == s["id"]
        assert proposal_event["reason"] == "завершено по заданию"
        comment_event = next(e for e in history if e["entity_type"] == "comment")
        assert comment_event["session_id"] == s["id"]


async def test_agent_cannot_review_own_result(db_session: AsyncSession, stub_user: User):
    w = await _world(db_session, stub_user)
    ctx = _ctx()
    with as_agent(db_session, w["agent"]):
        p = json.loads(await work.submit_result(ctx, str(w["task"].id), "готово"))
        assert json.loads(await work.list_review_queue(ctx)) == []
        with pytest.raises(McpError, match="SELF_REVIEW|NOT_REVIEWER"):
            await work.review_result(ctx, p["id"], "accepted", "сам проверил")


async def test_submit_result_retry_by_key(db_session: AsyncSession, stub_user: User):
    w = await _world(db_session, stub_user)
    tid = str(w["task"].id)
    ctx = _ctx()
    with as_agent(db_session, w["agent"]):
        first = await work.submit_result(ctx, tid, "готово", idempotency_key="res-1")
        again = await work.submit_result(ctx, tid, "готово", idempotency_key="res-1")
        assert json.loads(first)["id"] == json.loads(again)["id"]
        count = await db_session.scalar(select(func.count()).select_from(ResultProposal).where(
            ResultProposal.task_id == w["task"].id))
        assert count == 1

        with pytest.raises(McpError, match="IDEMPOTENCY_KEY_REUSED"):
            await work.submit_result(ctx, tid, "другое", idempotency_key="res-1")


async def test_work_package_not_ready(db_session: AsyncSession, stub_user: User):
    project = await project_service.create_project(
        db_session, ProjectCreate(name="NR", key=uuid.uuid4().hex[:8].upper()), stub_user
    )
    task = await task_service.create_task(db_session, project.id, TaskCreate(title="T"), stub_user)
    with as_agent(db_session, stub_user):
        assert json.loads(await work.get_work_package(_ctx(), str(task.id))) == {"state": "none"}
