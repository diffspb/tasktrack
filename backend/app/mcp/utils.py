import functools
import json
import uuid

from fastapi import HTTPException
from mcp.server.fastmcp.server import Context
from mcp.shared.exceptions import McpError
from mcp.types import ErrorData, INVALID_PARAMS, INTERNAL_ERROR

from app.core.db import SessionLocal
from app.mcp.auth import extract_bearer, get_user_for_key
from app.services import api_key_service, audit_service, idempotency_service, session_service


def parse_uuid(value: str, field: str = "id") -> uuid.UUID:
    try:
        return uuid.UUID(value)
    except ValueError:
        raise McpError(ErrorData(code=INVALID_PARAMS, message=f"Invalid UUID for {field}: {value!r}"))


class McpSession:
    """
    Async context manager: provides (AsyncSession, User) per tool call.

    Resolves the agent user from the Authorization: Bearer header:
    - service account key (tt_…, ADR-017) — checked against the DB on every call,
      exactly as REST does;
    - otherwise legacy MCP_AGENTS / dev-mode resolution (app.mcp.auth).

    Optional per-call context, the MCP counterparts of REST headers:
    - work_session — the caller's active work session (X-Task-Session, ADR-022);
    - reason — why the change is made (X-Change-Reason, ADR-018).
    """

    def __init__(self, ctx: Context, *, work_session: str | None = None, reason: str | None = None):
        self._ctx = ctx
        self._work_session = work_session
        self._reason = reason
        self._tokens: list = []

    async def __aenter__(self):
        api_key = extract_bearer(self._ctx.request_context.request.headers)
        self._session = SessionLocal()
        session = await self._session.__aenter__()
        try:
            if api_key_service.is_api_token(api_key):
                user = await api_key_service.authenticate(session, api_key)
                if user is None:
                    raise McpError(ErrorData(code=INVALID_PARAMS, message="Invalid or revoked API key."))
            else:
                user = get_user_for_key(api_key)
            row = (
                await session_service.resolve_header(session, self._work_session, user)
                if self._work_session else None
            )
        except BaseException:
            await self._session.__aexit__(None, None, None)
            raise
        self._tokens = [
            (session_service.current_session, session_service.current_session.set(row)),
            (audit_service.task_session_id, audit_service.task_session_id.set(row.id if row else None)),
            (audit_service.change_reason,
             audit_service.change_reason.set(audit_service.parse_reason_header(self._reason))),
        ]
        return session, user

    async def __aexit__(self, *args) -> None:
        for var, token in reversed(self._tokens):
            var.reset(token)
        await self._session.__aexit__(*args)


async def idempotent(session, user, key: str | None, tool: str, args: dict, call) -> str:
    """Safe retry of an MCP write by idempotency_key — same store and rules as REST (ADR-019):
    the reservation commits together with the command; a repeat returns the stored result."""
    if not key:
        return await call()
    body = json.dumps(args, sort_keys=True, default=str).encode()
    try:
        watermark = await idempotency_service.reserve(
            session, user, key, idempotency_service.request_hash("MCP", tool, body)
        )
    except idempotency_service.IdempotentReplay as replay:
        return replay.body
    try:
        result = await call()
    except BaseException:
        try:
            await idempotency_service.release(session, user.id, key)
        except Exception:  # session already failed; its rollback drops the reservation anyway
            pass
        raise
    await idempotency_service.complete(
        session, user.id, key, 200, result.encode(), "application/json", after_event_id=watermark
    )
    return result


def svc_call(fn):
    """Decorator: converts HTTPException from service layer → McpError."""
    @functools.wraps(fn)
    async def wrapper(*args, **kwargs):
        try:
            return await fn(*args, **kwargs)
        except HTTPException as e:
            detail = e.detail
            msg = detail.get("code", str(detail)) if isinstance(detail, dict) else str(detail)
            raise McpError(ErrorData(code=INTERNAL_ERROR, message=msg)) from e
    return wrapper
