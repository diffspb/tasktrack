import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_session
from app.models.user import User
from app.schemas.task import TaskCreate, TaskResponse, TaskStatusTransition, TaskUpdate
from app.services import task_service

router = APIRouter()


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


@router.get("/tasks", response_model=list[TaskResponse], tags=["tasks"])
async def list_tasks_global(
    project_ids: Annotated[list[uuid.UUID] | None, Query()] = None,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """Return tasks from all accessible projects (cross-project timeline view)."""
    return await task_service.list_tasks_global(session, user, project_ids=project_ids)
