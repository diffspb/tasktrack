"""Manager's control view (FR-003 TT-22)."""
import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_session
from app.models.user import User
from app.services import control_service

router = APIRouter(tags=["control"])


@router.get("/projects/{project_id}/control")
async def project_control(
    project_id: uuid.UUID,
    specialization: str | None = None,
    reviewer_id: uuid.UUID | None = None,
    reason: str | None = None,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """Open tasks with their waiting reasons and a summary by reason and specialization.

    Filters: specialization, reviewer_id, reason (see control_service for reason codes).
    """
    return await control_service.overview(
        session, project_id, user, specialization=specialization, reviewer_id=reviewer_id, reason=reason,
    )
