import uuid
from typing import Literal

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, ConfigDict
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_session
from app.models.user import User
from app.schemas.task import TaskResponse
from app.services import task_service

router = APIRouter(tags=["users"])


class UserMeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str
    display_name: str
    is_superuser: bool


@router.get("/users/me", response_model=UserMeResponse)
async def me(user: User = Depends(get_current_user)):
    return user


@router.get("/users/search", response_model=list[UserMeResponse])
async def search_users(
    q: str = Query(min_length=1, max_length=100),
    limit: int = Query(default=20, le=50),
    session: AsyncSession = Depends(get_session),
    _user: User = Depends(get_current_user),
):
    """Search users by display_name or email (case-insensitive, partial match)."""
    pattern = f"%{q.lower()}%"
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
        .limit(limit)
    )
    return list((await session.scalars(stmt)).all())


@router.get("/users/me/tasks", response_model=list[TaskResponse])
async def my_tasks(
    role: Literal["assignee", "reporter"] | None = Query(default=None),
    status_id: uuid.UUID | None = Query(default=None),
    project_id: uuid.UUID | None = Query(default=None),
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    return await task_service.list_my_tasks(
        session, user,
        role=role, status_id=status_id, project_id=project_id,
    )
