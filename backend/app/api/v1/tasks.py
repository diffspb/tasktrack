import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_session
from app.models.task import GlobalStatus
from app.models.user import User
from app.schemas.task import (
    AssignmentCreate,
    AssignmentResponse,
    AssignmentRoleUpdate,
    AssignmentTransition,
    TaskCreate,
    TaskResponse,
    TaskUpdate,
)
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
    global_status: GlobalStatus | None = None,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    return await task_service.list_tasks(session, project_id, user, global_status)


@router.get("/tasks/{task_id}", response_model=TaskResponse, tags=["tasks"])
async def get_task(
    task_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    return await task_service.get_task(session, task_id, user)


@router.patch("/tasks/{task_id}", response_model=TaskResponse, tags=["tasks"])
async def update_task(
    task_id: uuid.UUID,
    data: TaskUpdate,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    return await task_service.update_task(session, task_id, data, user)


@router.delete("/tasks/{task_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["tasks"])
async def delete_task(
    task_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    await task_service.delete_task(session, task_id, user)


@router.post(
    "/tasks/{task_id}/assignments",
    response_model=AssignmentResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["assignments"],
)
async def assign_user(
    task_id: uuid.UUID,
    data: AssignmentCreate,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    return await task_service.assign_user(session, task_id, data, user)


@router.patch(
    "/assignments/{assignment_id}/status",
    response_model=AssignmentResponse,
    tags=["assignments"],
)
async def transition_status(
    assignment_id: uuid.UUID,
    data: AssignmentTransition,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    return await task_service.transition_assignment_status(session, assignment_id, data, user)


@router.patch(
    "/assignments/{assignment_id}/role",
    response_model=AssignmentResponse,
    tags=["assignments"],
)
async def update_role(
    assignment_id: uuid.UUID,
    data: AssignmentRoleUpdate,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    return await task_service.update_assignment_role(session, assignment_id, data, user)


@router.delete(
    "/assignments/{assignment_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["assignments"],
)
async def remove_assignment(
    assignment_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    await task_service.remove_assignment(session, assignment_id, user)
