import uuid
from datetime import UTC, datetime

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.comment import Comment
from app.models.task import Task
from app.models.user import User
from app.schemas.comment import CommentCreate, CommentUpdate
from app.services.permissions import require_project_access


async def list_comments(
    session: AsyncSession, task_id: uuid.UUID, user: User
) -> list[Comment]:
    task = await _get_task_or_404(session, task_id)
    await require_project_access(session, task.project_id, user)

    rows = await session.scalars(
        select(Comment)
        .options(selectinload(Comment.replies))
        .where(
            Comment.task_id == task_id,
            Comment.parent_comment_id.is_(None),
            Comment.deleted_at.is_(None),
        )
        .order_by(Comment.created_at)
    )
    return list(rows.all())


async def create_comment(
    session: AsyncSession, task_id: uuid.UUID, data: CommentCreate, user: User
) -> Comment:
    task = await _get_task_or_404(session, task_id)
    await require_project_access(session, task.project_id, user)

    if data.parent_comment_id:
        parent = await session.get(Comment, data.parent_comment_id)
        if not parent or parent.task_id != task_id:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST, {"code": "PARENT_COMMENT_NOT_FOUND"}
            )
        if parent.parent_comment_id is not None:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST, {"code": "NESTING_TOO_DEEP"}
            )

    comment = Comment(
        task_id=task_id,
        author_id=user.id,
        parent_comment_id=data.parent_comment_id,
        content=data.content,
        labels=data.labels,
    )
    session.add(comment)
    await session.flush()

    if "solution" in data.labels:
        task.meta = {**task.meta, "solution_comment_id": str(comment.id)}

    await session.commit()
    await session.refresh(comment)
    return comment


async def update_comment(
    session: AsyncSession, comment_id: uuid.UUID, data: CommentUpdate, user: User
) -> Comment:
    comment = await _get_comment_or_404(session, comment_id)

    if comment.author_id != user.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, {"code": "PERMISSION_DENIED"})
    if comment.deleted_at is not None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, {"code": "COMMENT_NOT_FOUND"})

    comment.content = data.content
    comment.edited_at = datetime.now(UTC)
    await session.commit()
    await session.refresh(comment)
    return comment


async def delete_comment(
    session: AsyncSession, comment_id: uuid.UUID, user: User
) -> None:
    comment = await _get_comment_or_404(session, comment_id)
    task = await _get_task_or_404(session, comment.task_id)
    await require_project_access(session, task.project_id, user)

    is_author = comment.author_id == user.id
    from app.models.project import ProjectMember, ProjectMemberRole
    is_manager = await session.scalar(
        select(ProjectMember).where(
            ProjectMember.project_id == task.project_id,
            ProjectMember.user_id == user.id,
            ProjectMember.role.in_([ProjectMemberRole.admin, ProjectMemberRole.manager]),
        )
    )
    if not is_author and not is_manager:
        raise HTTPException(status.HTTP_403_FORBIDDEN, {"code": "PERMISSION_DENIED"})

    comment.deleted_at = datetime.now(UTC)

    if task.meta.get("solution_comment_id") == str(comment.id):
        meta = dict(task.meta)
        meta.pop("solution_comment_id", None)
        task.meta = meta

    await session.commit()


# --- Internal helpers ---

async def _get_task_or_404(session: AsyncSession, task_id: uuid.UUID) -> Task:
    task = await session.get(Task, task_id)
    if not task or task.deleted_at is not None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, {"code": "TASK_NOT_FOUND"})
    return task


async def _get_comment_or_404(session: AsyncSession, comment_id: uuid.UUID) -> Comment:
    comment = await session.get(Comment, comment_id)
    if not comment:
        raise HTTPException(status.HTTP_404_NOT_FOUND, {"code": "COMMENT_NOT_FOUND"})
    return comment
