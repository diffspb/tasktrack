import uuid

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict
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


@router.get("/users/me", response_model=UserMeResponse)
async def me(user: User = Depends(get_current_user)):
    return user


@router.get("/users/me/tasks", response_model=list[TaskResponse])
async def my_tasks(
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    return await task_service.list_my_tasks(session, user)
