import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_session
from app.models.user import User
from app.schemas.resolution import ResolutionCreate, ResolutionResponse, ResolutionUpdate
from app.services import resolution_service

router = APIRouter(tags=["resolutions"])


@router.get("/projects/{project_id}/resolutions", response_model=list[ResolutionResponse])
async def list_resolutions(
    project_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    return await resolution_service.list_resolutions(session, project_id, user)


@router.post(
    "/projects/{project_id}/resolutions",
    response_model=ResolutionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_resolution(
    project_id: uuid.UUID,
    data: ResolutionCreate,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    return await resolution_service.create_resolution(session, project_id, data, user)


@router.patch("/resolutions/{resolution_id}", response_model=ResolutionResponse)
async def update_resolution(
    resolution_id: uuid.UUID,
    data: ResolutionUpdate,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    return await resolution_service.update_resolution(session, resolution_id, data, user)


@router.delete("/resolutions/{resolution_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_resolution(
    resolution_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    await resolution_service.delete_resolution(session, resolution_id, user)
