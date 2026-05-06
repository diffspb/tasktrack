import functools
import uuid

from fastapi import HTTPException
from mcp.server.fastmcp import Context
from mcp.shared.exceptions import McpError
from mcp.types import ErrorData, INVALID_PARAMS, INTERNAL_ERROR

from app.core.db import SessionLocal
from app.mcp.auth import get_agent_user, check_api_key


def parse_uuid(value: str, field: str = "id") -> uuid.UUID:
    try:
        return uuid.UUID(value)
    except ValueError:
        raise McpError(ErrorData(code=INVALID_PARAMS, message=f"Invalid UUID for {field}: {value!r}"))


class McpSession:
    """Async context manager: provides (session, agent_user) per tool call."""

    def __init__(self, ctx: Context | None = None):
        self._ctx = ctx

    async def __aenter__(self) -> tuple:
        if self._ctx is not None:
            await check_api_key(self._ctx)
        self._session = SessionLocal()
        session = await self._session.__aenter__()
        return session, get_agent_user()

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
