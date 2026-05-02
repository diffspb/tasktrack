import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_session
from app.models.user import User
from app.schemas.comment import CommentCreate, CommentResponse, CommentUpdate
from app.services import comment_service

router = APIRouter()


@router.get("/tasks/{task_id}/comments", response_model=list[CommentResponse], tags=["comments"])
async def list_comments(
    task_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    return await comment_service.list_comments(session, task_id, user)


@router.post(
    "/tasks/{task_id}/comments",
    response_model=CommentResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["comments"],
)
async def create_comment(
    task_id: uuid.UUID,
    data: CommentCreate,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    return await comment_service.create_comment(session, task_id, data, user)


@router.patch("/comments/{comment_id}", response_model=CommentResponse, tags=["comments"])
async def update_comment(
    comment_id: uuid.UUID,
    data: CommentUpdate,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    return await comment_service.update_comment(session, comment_id, data, user)


@router.delete(
    "/comments/{comment_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["comments"],
)
async def delete_comment(
    comment_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    await comment_service.delete_comment(session, comment_id, user)
