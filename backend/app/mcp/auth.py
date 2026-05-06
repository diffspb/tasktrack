import uuid

from fastapi import HTTPException
from mcp.server.fastmcp.server import Context

from app.core.config import settings
from app.core.db import SessionLocal
from app.models.user import User

_agent_user: User | None = None


async def resolve_agent_user() -> User:
    """Called once at server startup. Caches the agent User in module state."""
    global _agent_user
    if settings.mcp_agent_user_id is None:
        raise RuntimeError(
            "MCP_AGENT_USER_ID is not set. Run 'make mcp-bootstrap' first."
        )
    async with SessionLocal() as session:
        user = await session.get(User, settings.mcp_agent_user_id)
        if user is None or not user.is_active:
            raise RuntimeError(
                f"Agent user {settings.mcp_agent_user_id} not found or inactive. "
                "Run 'make mcp-bootstrap' to create it."
            )
        _agent_user = user
    return _agent_user


def get_agent_user() -> User:
    if _agent_user is None:
        raise RuntimeError("Agent user not resolved — server not properly started.")
    return _agent_user


async def check_api_key(ctx: Context) -> None:
    """Middleware-style check: validates MCP_API_KEY if configured."""
    if not settings.mcp_api_key:
        return
    auth_header: str = (ctx.request_context.request.headers.get("authorization") or "")
    scheme, _, token = auth_header.partition(" ")
    if scheme.lower() != "bearer" or token != settings.mcp_api_key:
        raise HTTPException(status_code=401, detail="Invalid MCP API key")
