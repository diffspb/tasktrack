"""
Centralized access-control helpers.
All service modules import from here instead of project_service internals.
"""
import uuid

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.project import ProjectMember, ProjectMemberRole
from app.models.user import User


async def get_member(
    session: AsyncSession, project_id: uuid.UUID, user_id: uuid.UUID
) -> ProjectMember | None:
    return await session.scalar(
        select(ProjectMember).where(
            ProjectMember.project_id == project_id,
            ProjectMember.user_id == user_id,
        )
    )


async def require_project_access(
    session: AsyncSession, project_id: uuid.UUID, user: User
) -> None:
    """Raises 404 if project doesn't exist or user can't see it."""
    from app.services.project_service import get_project

    await get_project(session, project_id, user)


async def require_manager(
    session: AsyncSession, project_id: uuid.UUID, user: User
) -> None:
    """Raises 404 if no project access, 403 if not admin/manager."""
    await require_project_access(session, project_id, user)
    member = await get_member(session, project_id, user.id)
    if not member or member.role not in (ProjectMemberRole.admin, ProjectMemberRole.manager):
        raise HTTPException(status.HTTP_403_FORBIDDEN, {"code": "PERMISSION_DENIED"})
