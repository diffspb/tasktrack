from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.bootstrap import ensure_system_data
from app.core.db import get_session
from app.models.user import User

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/system-status")
async def system_status(
    session: AsyncSession = Depends(get_session),
    _: User = Depends(get_current_user),
):
    from app.models.task_type import TaskType

    count = await session.scalar(
        select(func.count()).select_from(TaskType).where(TaskType.is_system.is_(True))
    )
    return {"initialized": bool(count)}


@router.post("/initialize")
async def initialize_system(
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    if not user.is_superuser:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail={"code": "PERMISSION_DENIED"})
    await ensure_system_data()
    return {"ok": True}
