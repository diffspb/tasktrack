import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_session
from app.models.user import User
from app.schemas.task import TaskCreate, TaskLinkCreate, TaskLinkResponse, TaskResponse, TaskStatusTransition, TaskUpdate
from app.services import task_link_service, task_service

router = APIRouter()


@router.get("/task-types", tags=["tasks"])
async def list_task_types(
    session: AsyncSession = Depends(get_session),
    _: User = Depends(get_current_user),
):
    from app.models.task_type import TaskType
    from app.schemas.task_type import TaskTypeResponse

    types = await session.scalars(
        select(TaskType)
        .where(TaskType.is_system.is_(True))
        .order_by(TaskType.name)
    )
    return {"items": [TaskTypeResponse.model_validate(t) for t in types]}


@router.post(
    "/projects/{project_id}/tasks",
    response_model=TaskResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["tasks"],
)
async def create_task(
    project_id: uuid.UUID,
    data: TaskCreate,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    return await task_service.create_task(session, project_id, data, user)


@router.get("/projects/{project_id}/tasks", response_model=list[TaskResponse], tags=["tasks"])
async def list_tasks(
    project_id: uuid.UUID,
    status_id: uuid.UUID | None = None,
    assignee_id: uuid.UUID | None = None,
    task_type_key: str | None = None,
    parent_task_id: uuid.UUID | None = None,
    include_subtasks: bool = True,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    return await task_service.list_tasks(
        session, project_id, user,
        status_id=status_id,
        assignee_id=assignee_id,
        task_type_key=task_type_key,
        parent_task_id=parent_task_id,
        include_subtasks=include_subtasks,
    )


@router.get("/tasks/{task_id}", response_model=TaskResponse, tags=["tasks"])
async def get_task(
    task_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    return await task_service.get_task(session, task_id, user)


@router.get("/tasks/by-key/{key}", response_model=TaskResponse, tags=["tasks"])
async def get_task_by_key(
    key: str,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    return await task_service.get_task_by_key(session, key, user)


@router.patch("/tasks/{task_id}", response_model=TaskResponse, tags=["tasks"])
async def update_task(
    task_id: uuid.UUID,
    data: TaskUpdate,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    return await task_service.update_task(session, task_id, data, user)


@router.post(
    "/tasks/{task_id}/transition",
    response_model=TaskResponse,
    tags=["tasks"],
)
async def transition_status(
    task_id: uuid.UUID,
    data: TaskStatusTransition,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    return await task_service.transition_status(session, task_id, data, user)


@router.delete("/tasks/{task_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["tasks"])
async def delete_task(
    task_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    await task_service.delete_task(session, task_id, user)


@router.get("/tasks/{task_id}/links", response_model=list[TaskLinkResponse], tags=["tasks"])
async def get_task_links(
    task_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    return await task_link_service.get_task_links(session, task_id, user)


@router.post("/tasks/{task_id}/links", response_model=TaskLinkResponse, status_code=status.HTTP_201_CREATED, tags=["tasks"])
async def create_task_link(
    task_id: uuid.UUID,
    data: TaskLinkCreate,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    return await task_link_service.create_task_link(session, task_id, data, user)


@router.delete("/tasks/{task_id}/links/{link_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["tasks"])
async def delete_task_link(
    task_id: uuid.UUID,
    link_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    await task_link_service.delete_task_link(session, task_id, link_id, user)


@router.get("/tasks", response_model=list[TaskResponse], tags=["tasks"])
async def list_tasks_global(
    project_ids: Annotated[list[uuid.UUID] | None, Query()] = None,
    q: str | None = None,
    task_type_keys: Annotated[list[str] | None, Query()] = None,
    limit: int = 50,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """Return tasks from all accessible projects. When q is provided, searches by key or title."""
    return await task_service.list_tasks_global(
        session, user,
        project_ids=project_ids,
        q=q,
        task_type_keys=task_type_keys,
        limit=limit,
    )
