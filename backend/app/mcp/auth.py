import uuid

from mcp.server.fastmcp.server import Context
from mcp.shared.exceptions import McpError
from mcp.types import ErrorData, INVALID_PARAMS

from app.core.config import settings
from app.core.db import SessionLocal
from app.models.user import User

# api_key → User; empty string key = dev mode (no key required)
_agents: dict[str, User] = {}
_dev_user: User | None = None  # used when mcp_agents is empty


def _parse_agents_env(raw: str) -> dict[str, uuid.UUID]:
    """Parse "key1:uuid1,key2:uuid2" into {key: UUID}."""
    result: dict[str, uuid.UUID] = {}
    for pair in raw.split(","):
        pair = pair.strip()
        if ":" not in pair:
            continue
        key, uid_str = pair.split(":", 1)
        key = key.strip()
        if key:
            result[key.strip()] = uuid.UUID(uid_str.strip())
    return result


async def resolve_all_agents() -> None:
    """
    Called once at server startup. Loads all agent users from DB.

    Two modes:
    - MCP_AGENTS set: parse key→UUID map, load each User, require key on every call
    - MCP_AGENTS empty + MCP_AGENT_USER_ID set: single dev user, no key required
    """
    global _agents, _dev_user

    if settings.mcp_agents:
        mapping = _parse_agents_env(settings.mcp_agents)
        if not mapping:
            print("[MCP] Warning: MCP_AGENTS is set but could not be parsed. Expected format: key1:uuid1,key2:uuid2")
            return
        async with SessionLocal() as session:
            for key, uid in mapping.items():
                user = await session.get(User, uid)
                if user is None or not user.is_active:
                    print(f"[MCP] Warning: agent user {uid} (key={key!r}) not found or inactive — skipped.")
                    continue
                _agents[key] = user
        if _agents:
            print(f"[MCP] Loaded {len(_agents)} agent(s): {', '.join(_agents)}")
        else:
            print("[MCP] Warning: no agent users could be loaded. MCP tools will fail until DB is populated.")
    elif settings.mcp_agent_user_id is not None:
        async with SessionLocal() as session:
            user = await session.get(User, settings.mcp_agent_user_id)
            if user is None or not user.is_active:
                print(
                    f"[MCP] Warning: agent user {settings.mcp_agent_user_id} not found or inactive. "
                    "Run 'make mcp-bootstrap' to create it."
                )
                return
            _dev_user = user
        print(f"[MCP] Dev mode: single agent user '{_dev_user.email}'")
    else:
        print("[MCP] Warning: neither MCP_AGENTS nor MCP_AGENT_USER_ID set. MCP tools will fail.")


def get_user_for_key(api_key: str | None) -> User:
    """
    Return User for the given API key.

    - Multi-agent mode (MCP_AGENTS set): key must match a registered agent.
    - Dev mode (MCP_AGENT_USER_ID only): key is ignored, returns the single dev user.
    """
    if _agents:
        if not api_key or api_key not in _agents:
            raise McpError(ErrorData(
                code=INVALID_PARAMS,
                message="Invalid or missing MCP API key. Set Authorization: Bearer <key>.",
            ))
        return _agents[api_key]

    if _dev_user is not None:
        return _dev_user

    raise McpError(ErrorData(
        code=INVALID_PARAMS,
        message="MCP server not configured. Run 'make mcp-bootstrap' and set MCP_AGENT_USER_ID.",
    ))


def extract_bearer(headers) -> str | None:
    """Extract bearer token from Authorization header (case-insensitive)."""
    auth: str = headers.get("authorization") or ""
    scheme, _, token = auth.partition(" ")
    return token if scheme.lower() == "bearer" and token else None
