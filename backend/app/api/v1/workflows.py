import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_session
from app.models.user import User
from app.schemas.workflow import (
    MigrateStatus,
    StatusCreate,
    StatusResponse,
    StatusUpdate,
    TransitionCreate,
    TransitionResponse,
    WorkflowCreate,
    WorkflowResponse,
    WorkflowUpdate,
)
from app.services import workflow_service

router = APIRouter()


@router.post(
    "/projects/{project_id}/workflows",
    response_model=WorkflowResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["workflows"],
)
async def create_workflow(
    project_id: uuid.UUID,
    data: WorkflowCreate,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    return await workflow_service.create_workflow(session, project_id, data, user)


@router.get("/projects/{project_id}/workflows", response_model=list[WorkflowResponse], tags=["workflows"])
async def list_workflows(
    project_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    return await workflow_service.list_workflows(session, project_id, user)


@router.get("/workflows/{workflow_id}", response_model=WorkflowResponse, tags=["workflows"])
async def get_workflow(
    workflow_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    return await workflow_service.get_workflow(session, workflow_id, user)


@router.patch("/workflows/{workflow_id}", response_model=WorkflowResponse, tags=["workflows"])
async def update_workflow(
    workflow_id: uuid.UUID,
    data: WorkflowUpdate,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    return await workflow_service.update_workflow(session, workflow_id, data, user)


@router.delete("/workflows/{workflow_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["workflows"])
async def delete_workflow(
    workflow_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    await workflow_service.delete_workflow(session, workflow_id, user)


@router.post(
    "/workflows/{workflow_id}/statuses",
    response_model=StatusResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["statuses"],
)
async def create_status(
    workflow_id: uuid.UUID,
    data: StatusCreate,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    return await workflow_service.create_status(session, workflow_id, data, user)


@router.patch("/statuses/{status_id}", response_model=StatusResponse, tags=["statuses"])
async def update_status(
    status_id: uuid.UUID,
    data: StatusUpdate,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    return await workflow_service.update_status(session, status_id, data, user)


@router.delete("/statuses/{status_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["statuses"])
async def delete_status(
    status_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    await workflow_service.delete_status(session, status_id, user)


@router.post("/statuses/{status_id}/migrate", status_code=status.HTTP_200_OK, tags=["statuses"])
async def migrate_status(
    status_id: uuid.UUID,
    data: MigrateStatus,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    await workflow_service.migrate_status(session, status_id, data, user)
    return {"status": "migrated"}


@router.post(
    "/workflows/{workflow_id}/transitions",
    response_model=TransitionResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["transitions"],
)
async def create_transition(
    workflow_id: uuid.UUID,
    data: TransitionCreate,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    return await workflow_service.create_transition(session, workflow_id, data, user)


@router.delete("/transitions/{transition_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["transitions"])
async def delete_transition(
    transition_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    await workflow_service.delete_transition(session, transition_id, user)
