"""X-Task-Session header (ADR-022, FR-003 TT-12).

An agent names its active work session once per request; changes made in the
request are recorded against that session (audit events, result proposals).
The header must name the caller's own active session — otherwise 409.
"""
from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.db import get_session
from app.models.user import User
from app.services import audit_service, session_service

HEADER = "x-task-session"


async def task_session_guard(
    request: Request,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
) -> None:
    raw = request.headers.get(HEADER)
    row = await session_service.resolve_header(session, raw, user) if raw else None
    # Always set (also to None): in-process test transports reuse one context across requests.
    session_service.current_session.set(row)
    audit_service.task_session_id.set(row.id if row else None)
