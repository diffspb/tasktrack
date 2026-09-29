"""Durable audit log / event journal (ADR-018, FR-003 TT-06)."""
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_session
from app.models.user import User
from app.schemas.audit import AuditPage
from app.services import audit_service, task_service
from app.services.permissions import require_project_access

router = APIRouter(tags=["audit"])

_After = Query(None, description="Cursor from a previous page's next_cursor")
_Limit = Query(audit_service.DEFAULT_LIMIT, ge=1, le=audit_service.MAX_LIMIT)


@router.get("/projects/{project_id}/audit-log", response_model=AuditPage)
async def project_audit_log(
    project_id: uuid.UUID,
    after: str | None = _After,
    limit: int = _Limit,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    await require_project_access(session, project_id, user)
    return await audit_service.list_events(session, project_id=project_id, after=after, limit=limit)


@router.get("/tasks/{task_id}/history", response_model=AuditPage)
async def task_history(
    task_id: uuid.UUID,
    after: str | None = _After,
    limit: int = _Limit,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    await task_service.get_task(session, task_id, user)  # read access
    return await audit_service.list_events(session, task_id=task_id, after=after, limit=limit)


@router.get("/admin/audit-log", response_model=AuditPage)
async def system_audit_log(
    after: str | None = _After,
    limit: int = _Limit,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """System-level events (service accounts, API keys) — superuser only."""
    if not user.is_superuser:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail={"code": "PERMISSION_DENIED"})
    return await audit_service.list_events(session, system=True, after=after, limit=limit)
