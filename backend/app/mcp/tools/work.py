"""Agent work contract over MCP (FR-003 TT-18): assignment → session → result → review.

The same contract as REST: every call checks project access, author and versions.
Write tools accept:
- idempotency_key — safe retry after a lost response (ADR-019);
- session_id — the caller's active work session (ADR-022);
- reason — why the change is made, recorded in the audit log (ADR-018).
"""
import json

from mcp.server.fastmcp.server import Context

from app.mcp.utils import McpSession, idempotent, parse_uuid, svc_call
from app.schemas.audit import AuditPage
from app.schemas.result import ProposalCreate, ProposalResponse, ReviewCreate, ReviewResponse
from app.schemas.session import (
    CheckpointCreate, CheckpointResponse, SessionComplete, SessionCreate, SessionRelease, SessionResponse,
)
from app.services import audit_service, result_service, session_service, task_service, work_package_service


def _dump(model_cls, obj) -> str:
    return json.dumps(model_cls.model_validate(obj).model_dump(mode="json"), ensure_ascii=False)


@svc_call
async def get_work_package(ctx: Context, task_id: str) -> str:
    """
    The task's current assignment as a pinned copy: id, version, digest, content
    (goal, expected_result, criteria with keys c1…, inputs, constraints, specialization).

    Work against this exact version; cite criterion keys in submit_result.
    Returns {"state": "none"|"draft"} if no version has been issued yet — the task is not ready.
    """
    async with McpSession(ctx) as (session, user):
        tid = parse_uuid(task_id, "task_id")
        state = await work_package_service.get_state(session, tid, user)
        if state["current"] is None:
            return json.dumps({"state": state["state"]})
        return json.dumps(await work_package_service.export(session, state["current"].id, user), ensure_ascii=False)


@svc_call
async def claim_task(
    ctx: Context,
    task_id: str,
    machine: str | None = None,
    workdir: str | None = None,
    client: str | None = None,
    idempotency_key: str | None = None,
) -> str:
    """
    Start a work session on a task you are assigned to. Returns the session (id, pinned
    work_package_id). Pass its id as session_id to later calls.

    Fails with SESSION_ACTIVE if another session holds the task — even your own from
    another process. Do not take over: the other process must be verified stopped and
    the session released (release_session) first. Losing connection never ends a session.
    """
    args = {"task_id": task_id, "machine": machine, "workdir": workdir, "client": client}
    async with McpSession(ctx) as (session, user):
        async def call():
            row = await session_service.claim(
                session, parse_uuid(task_id, "task_id"),
                SessionCreate(machine=machine, workdir=workdir, client=client), user,
            )
            return _dump(SessionResponse, row)
        return await idempotent(session, user, idempotency_key, "claim_task", args, call)


@svc_call
async def checkpoint(ctx: Context, session_id: str, note: str, data: dict | None = None) -> str:
    """
    Save a checkpoint in your session: after a significant result and before a long or
    external action. Recovery after a crash starts from the last checkpoint.
    """
    async with McpSession(ctx) as (session, user):
        cp = await session_service.add_checkpoint(
            session, parse_uuid(session_id, "session_id"), CheckpointCreate(note=note, data=data or {}), user,
        )
        return _dump(CheckpointResponse, cp)


@svc_call
async def finish_session(ctx: Context, session_id: str, result: str | None = None) -> str:
    """Complete your work session (after submit_result, or when stopping work deliberately)."""
    async with McpSession(ctx) as (session, user):
        row = await session_service.complete(
            session, parse_uuid(session_id, "session_id"), SessionComplete(result=result), user,
        )
        return _dump(SessionResponse, row)


@svc_call
async def release_session(ctx: Context, session_id: str, reason: str) -> str:
    """
    End a session by explicit decision — yours, or (as manager) someone else's after the
    process was verified stopped. reason is required.
    """
    async with McpSession(ctx) as (session, user):
        row = await session_service.release(
            session, parse_uuid(session_id, "session_id"), SessionRelease(reason=reason), user,
        )
        return _dump(SessionResponse, row)


@svc_call
async def submit_result(
    ctx: Context,
    task_id: str,
    summary: str,
    links: list[dict] | None = None,
    criteria: list[dict] | None = None,
    checks: list[dict] | None = None,
    limitations: str | None = None,
    supersedes_id: str | None = None,
    session_id: str | None = None,
    reason: str | None = None,
    idempotency_key: str | None = None,
) -> str:
    """
    Present the result of a task you are assigned to (a result proposal). Immutable once
    submitted; to correct it after "changes_requested", submit a new one with supersedes_id.

    links: [{"kind": "pr"|"commit"|"release"|"build"|"document"|"other", "url": ..., "ref": ...}]
    criteria: [{"key": "c1", "status": "met"|"not_met"|"not_applicable", "evidence": ...}] —
              keys of the work package criteria (get_work_package).
    checks: [{"name": ..., "result": "passed"|"failed"|"skipped", "details": ...}]
    session_id: your active session — the proposal is bound to it and its assignment version.
    A comment is never a result: only submit_result counts.
    """
    args = {"task_id": task_id, "summary": summary, "links": links, "criteria": criteria,
            "checks": checks, "limitations": limitations, "supersedes_id": supersedes_id}
    async with McpSession(ctx, work_session=session_id, reason=reason) as (session, user):
        async def call():
            data = ProposalCreate(
                summary=summary, links=links or [], criteria=criteria or [], checks=checks or [],
                limitations=limitations,
                supersedes_id=parse_uuid(supersedes_id, "supersedes_id") if supersedes_id else None,
            )
            proposal = await result_service.submit_proposal(session, parse_uuid(task_id, "task_id"), data, user)
            return _dump(ProposalResponse, proposal)
        return await idempotent(session, user, idempotency_key, "submit_result", args, call)


@svc_call
async def list_results(ctx: Context, task_id: str) -> str:
    """All result proposal versions of a task with their reviews."""
    async with McpSession(ctx) as (session, user):
        proposals = await result_service.list_proposals(session, parse_uuid(task_id, "task_id"), user)
        return json.dumps([ProposalResponse.model_validate(p).model_dump(mode="json") for p in proposals],
                          ensure_ascii=False)


@svc_call
async def list_review_queue(ctx: Context, project_id: str | None = None) -> str:
    """Result proposals waiting for your review (you need the reviewer profile in the project)."""
    async with McpSession(ctx) as (session, user):
        pid = parse_uuid(project_id, "project_id") if project_id else None
        proposals = await result_service.review_queue(session, user, project_id=pid)
        return json.dumps([ProposalResponse.model_validate(p).model_dump(mode="json") for p in proposals],
                          ensure_ascii=False)


@svc_call
async def review_result(
    ctx: Context,
    proposal_id: str,
    verdict: str,
    rationale: str,
    criteria: list[dict] | None = None,
    session_id: str | None = None,
    idempotency_key: str | None = None,
) -> str:
    """
    Review a result proposal: verdict "accepted" | "changes_requested" | "rejected".

    rationale is required. "accepted" needs every required criterion of the assignment
    marked met: criteria=[{"key": "c1", "verdict": "met"|"not_met", "note": ...}].
    You cannot review your own result or a task you are assigned to.
    """
    args = {"proposal_id": proposal_id, "verdict": verdict, "rationale": rationale, "criteria": criteria}
    async with McpSession(ctx, work_session=session_id) as (session, user):
        async def call():
            data = ReviewCreate(verdict=verdict, rationale=rationale, criteria=criteria or [])
            review = await result_service.review_proposal(session, parse_uuid(proposal_id, "proposal_id"), data, user)
            return _dump(ReviewResponse, review)
        return await idempotent(session, user, idempotency_key, "review_result", args, call)


@svc_call
async def get_task_history(ctx: Context, task_id: str, after: str | None = None, limit: int = 100) -> str:
    """
    Durable change history of a task (task, comments, links, assignment, sessions, results,
    reviews): who, when, why, before/after. Page with next_cursor → after.
    """
    async with McpSession(ctx) as (session, user):
        tid = parse_uuid(task_id, "task_id")
        await task_service.get_task(session, tid, user)
        page = await audit_service.list_events(session, task_id=tid, after=after, limit=limit)
        return AuditPage.model_validate(
            {"items": page.items, "next_cursor": page.next_cursor}, from_attributes=True,
        ).model_dump_json()

