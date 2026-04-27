import re
import uuid

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.project import Project, ProjectMember, ProjectMemberRole, ProjectVisibility
from app.models.user import User
from app.schemas.project import ProjectCreate, ProjectMemberAdd, ProjectUpdate


async def create_project(session: AsyncSession, data: ProjectCreate, owner: User) -> Project:
    project = Project(
        name=data.name,
        key=data.key,
        description=data.description,
        visibility=data.visibility,
        owner_id=owner.id,
    )
    try:
        session.add(project)
        await session.flush()
        session.add(ProjectMember(project_id=project.id, user_id=owner.id, role=ProjectMemberRole.admin))
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, {"code": "DUPLICATE_PROJECT_KEY"})

    return await _load_project(session, project.id)


async def get_project(
    session: AsyncSession, project_id: uuid.UUID, user: User
) -> Project:
    project = await _load_project(session, project_id)
    if not project or project.deleted_at is not None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, {"code": "PROJECT_NOT_FOUND"})

    if project.visibility == ProjectVisibility.restricted:
        if not await get_member(session, project_id, user.id):
            raise HTTPException(status.HTTP_404_NOT_FOUND, {"code": "PROJECT_NOT_FOUND"})

    return project


async def list_projects(session: AsyncSession, user: User) -> list[Project]:
    member_subq = select(ProjectMember.project_id).where(ProjectMember.user_id == user.id)
    stmt = (
        select(Project)
        .options(selectinload(Project.members))
        .where(
            Project.deleted_at.is_(None),
            Project.is_archived == False,  # noqa: E712
            (Project.visibility == ProjectVisibility.public) | (Project.id.in_(member_subq)),
        )
    )
    return list((await session.scalars(stmt)).all())


async def update_project(
    session: AsyncSession, project_id: uuid.UUID, data: ProjectUpdate, user: User
) -> Project:
    project = await get_project(session, project_id, user)

    member = await get_member(session, project_id, user.id)
    if not member or member.role not in (ProjectMemberRole.admin, ProjectMemberRole.manager):
        raise HTTPException(status.HTTP_403_FORBIDDEN, {"code": "PERMISSION_DENIED"})

    if data.version != project.version:
        raise HTTPException(status.HTTP_409_CONFLICT, {"code": "VERSION_CONFLICT"})

    if data.name is not None:
        project.name = data.name
    if data.description is not None:
        project.description = data.description
    project.version += 1

    await session.commit()
    return await _load_project(session, project.id)


async def archive_project(
    session: AsyncSession, project_id: uuid.UUID, user: User
) -> Project:
    project = await get_project(session, project_id, user)

    member = await get_member(session, project_id, user.id)
    if not member or member.role != ProjectMemberRole.admin:
        raise HTTPException(status.HTTP_403_FORBIDDEN, {"code": "PERMISSION_DENIED"})

    project.is_archived = True
    await session.commit()
    return await _load_project(session, project.id)


async def add_member(
    session: AsyncSession, project_id: uuid.UUID, data: ProjectMemberAdd, user: User
) -> ProjectMember:
    await get_project(session, project_id, user)

    member = await get_member(session, project_id, user.id)
    if not member or member.role not in (ProjectMemberRole.admin, ProjectMemberRole.manager):
        raise HTTPException(status.HTTP_403_FORBIDDEN, {"code": "PERMISSION_DENIED"})

    if await get_member(session, project_id, data.user_id):
        raise HTTPException(status.HTTP_409_CONFLICT, {"code": "PROJECT_MEMBER_ALREADY_EXISTS"})

    new_member = ProjectMember(project_id=project_id, user_id=data.user_id, role=data.role)
    session.add(new_member)
    await session.commit()
    await session.refresh(new_member)
    return new_member


async def remove_member(
    session: AsyncSession, project_id: uuid.UUID, user_id: uuid.UUID, user: User
) -> None:
    await get_project(session, project_id, user)

    member = await get_member(session, project_id, user.id)
    if not member or member.role not in (ProjectMemberRole.admin, ProjectMemberRole.manager):
        raise HTTPException(status.HTTP_403_FORBIDDEN, {"code": "PERMISSION_DENIED"})

    target = await get_member(session, project_id, user_id)
    if not target:
        raise HTTPException(status.HTTP_404_NOT_FOUND, {"code": "PROJECT_MEMBER_NOT_FOUND"})

    await session.delete(target)
    await session.commit()


async def _load_project(session: AsyncSession, project_id: uuid.UUID) -> Project | None:
    return await session.scalar(
        select(Project)
        .options(selectinload(Project.members))
        .where(Project.id == project_id)
    )


async def get_member(
    session: AsyncSession, project_id: uuid.UUID, user_id: uuid.UUID
) -> ProjectMember | None:
    return await session.scalar(
        select(ProjectMember).where(
            ProjectMember.project_id == project_id,
            ProjectMember.user_id == user_id,
        )
    )
