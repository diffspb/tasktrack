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


_ROLE_RANK = {
    ProjectMemberRole.viewer: 0,
    ProjectMemberRole.member: 1,
    ProjectMemberRole.manager: 2,
    ProjectMemberRole.admin: 3,
}


def has_role(member: ProjectMember | None, minimum: ProjectMemberRole) -> bool:
    return member is not None and _ROLE_RANK[member.role] >= _ROLE_RANK[minimum]


async def require_role(
    session: AsyncSession, project_id: uuid.UUID, user: User, minimum: ProjectMemberRole
) -> ProjectMember:
    """Raises 404 if no project access, 403 if the user's project role is below `minimum`.

    Visibility of a public project grants reading only; any write requires membership.
    """
    await require_project_access(session, project_id, user)
    member = await get_member(session, project_id, user.id)
    if not has_role(member, minimum):
        raise HTTPException(status.HTTP_403_FORBIDDEN, {"code": "PERMISSION_DENIED"})
    return member


async def require_writer(
    session: AsyncSession, project_id: uuid.UUID, user: User
) -> ProjectMember:
    """Raises 404 if no project access, 403 if viewer or not a member."""
    return await require_role(session, project_id, user, ProjectMemberRole.member)


async def require_manager(
    session: AsyncSession, project_id: uuid.UUID, user: User
) -> ProjectMember:
    """Raises 404 if no project access, 403 if not admin/manager."""
    return await require_role(session, project_id, user, ProjectMemberRole.manager)


def visible_project_ids(user: User):
    """Subquery of project ids the user can read: public or member, not deleted."""
    from app.models.project import Project, ProjectVisibility

    member_ids = select(ProjectMember.project_id).where(ProjectMember.user_id == user.id)
    return select(Project.id).where(
        Project.deleted_at.is_(None),
        (Project.visibility == ProjectVisibility.public) | Project.id.in_(member_ids),
    )
