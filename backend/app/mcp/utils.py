import functools
import uuid

from fastapi import HTTPException
from mcp.server.fastmcp.server import Context
from mcp.shared.exceptions import McpError
from mcp.types import ErrorData, INVALID_PARAMS, INTERNAL_ERROR

from app.core.db import SessionLocal
from app.mcp.auth import extract_bearer, get_user_for_key
from app.services import api_key_service


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
    """

    def __init__(self, ctx: Context):
        self._ctx = ctx

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
        except BaseException:
            await self._session.__aexit__(None, None, None)
            raise
        return session, user

    async def __aexit__(self, *args) -> None:
        await self._session.__aexit__(*args)


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
