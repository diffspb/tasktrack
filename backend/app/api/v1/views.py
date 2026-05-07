import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_session
from app.models.user import User
from app.schemas.workflow import (
    AddStatusToColumn,
    BoardColumnCreate,
    BoardColumnResponse,
    BoardColumnUpdate,
    ViewCreate,
    ViewResponse,
    ViewUpdate,
)
from app.services import workflow_service

router = APIRouter()


# ── Views ─────────────────────────────────────────────────────────────────────

@router.get("/projects/{project_id}/views", response_model=list[ViewResponse], tags=["views"])
async def list_views(
    project_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    return await workflow_service.list_views(session, project_id, user)


@router.post(
    "/projects/{project_id}/views",
    response_model=ViewResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["views"],
)
async def create_view(
    project_id: uuid.UUID,
    data: ViewCreate,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    return await workflow_service.create_view(session, project_id, data, user)


@router.get("/views/{view_id}", response_model=ViewResponse, tags=["views"])
async def get_view(
    view_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    return await workflow_service.get_view(session, view_id, user)


@router.patch("/views/{view_id}", response_model=ViewResponse, tags=["views"])
async def update_view(
    view_id: uuid.UUID,
    data: ViewUpdate,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    return await workflow_service.update_view(session, view_id, data, user)


@router.delete("/views/{view_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["views"])
async def delete_view(
    view_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    await workflow_service.delete_view(session, view_id, user)


# ── Board columns (per view) ──────────────────────────────────────────────────

@router.get("/views/{view_id}/columns", tags=["views"])
async def list_columns(
    view_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    v = await workflow_service.get_view(session, view_id, user)
    cols = await workflow_service.get_board_columns(session, v.id)
    return {"items": [BoardColumnResponse(
        id=c.id, view_id=c.view_id, name=c.name, position=c.position,
        status_ids=c.status_ids, created_at=c.created_at, updated_at=c.updated_at,
    ) for c in cols]}


@router.post(
    "/views/{view_id}/columns",
    status_code=status.HTTP_201_CREATED,
    tags=["views"],
)
async def create_column(
    view_id: uuid.UUID,
    data: BoardColumnCreate,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    col = await workflow_service.create_board_column(session, view_id, data, user)
    return BoardColumnResponse(
        id=col.id, view_id=col.view_id, name=col.name, position=col.position,
        status_ids=col.status_ids, created_at=col.created_at, updated_at=col.updated_at,
    )


@router.patch("/board-columns/{column_id}", tags=["views"])
async def update_column(
    column_id: uuid.UUID,
    data: BoardColumnUpdate,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    col = await workflow_service.update_board_column(session, column_id, data, user)
    return BoardColumnResponse(
        id=col.id, view_id=col.view_id, name=col.name, position=col.position,
        status_ids=col.status_ids, created_at=col.created_at, updated_at=col.updated_at,
    )


@router.delete(
    "/board-columns/{column_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["views"],
)
async def delete_column(
    column_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    await workflow_service.delete_board_column(session, column_id, user)


@router.post("/board-columns/{column_id}/statuses", tags=["views"])
async def add_status(
    column_id: uuid.UUID,
    data: AddStatusToColumn,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    col = await workflow_service.add_status_to_column(session, column_id, data.status_id, user)
    return BoardColumnResponse(
        id=col.id, view_id=col.view_id, name=col.name, position=col.position,
        status_ids=col.status_ids, created_at=col.created_at, updated_at=col.updated_at,
    )


@router.delete(
    "/board-columns/{column_id}/statuses/{status_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["views"],
)
async def remove_status(
    column_id: uuid.UUID,
    status_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    await workflow_service.remove_status_from_column(session, column_id, status_id, user)
