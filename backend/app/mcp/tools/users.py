import json

from mcp.server.fastmcp.server import Context
from sqlalchemy import func, or_, select

from app.mcp.utils import McpSession, svc_call
from app.models.user import User


@svc_call
async def search_users(ctx: Context, query: str, limit: int = 20) -> str:
    """
    Search active users by display_name or email (case-insensitive partial match).

    Use this to resolve a person's name or email to a user UUID before passing
    assignee_id to create_task / update_task.

    query: search term, 1-100 chars (e.g. "alice" or "@example.com").
    limit: max results, 1-50, default 20.

    Returns: list of {id, email, display_name, is_superuser}.
    """
    async with McpSession(ctx) as (session, _user):
        q = (query or "").strip().lower()
        if not q:
            return json.dumps([])
        pattern = f"%{q}%"
        capped = min(max(limit, 1), 50)
        stmt = (
            select(User)
            .where(
                User.is_active.is_(True),
                or_(
                    func.lower(User.display_name).like(pattern),
                    func.lower(User.email).like(pattern),
                ),
            )
            .order_by(User.display_name)
            .limit(capped)
        )
        rows = list((await session.scalars(stmt)).all())
        return json.dumps([
            {
                "id": str(u.id),
                "email": u.email,
                "display_name": u.display_name,
                "is_superuser": u.is_superuser,
            }
            for u in rows
        ])
