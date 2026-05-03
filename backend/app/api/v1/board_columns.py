import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_session
from app.models.user import User
from app.schemas.workflow import AddStatusToColumn, BoardColumnResponse, BoardColumnUpdate
from app.services import workflow_service

router = APIRouter(prefix="/board-columns", tags=["board-columns"])


@router.patch("/{column_id}")
async def update_board_column(
    column_id: uuid.UUID,
    data: BoardColumnUpdate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    col = await workflow_service.update_board_column(session, column_id, data, current_user)
    return BoardColumnResponse(
        id=col.id, project_id=col.project_id, name=col.name, position=col.position,
        status_ids=col.status_ids, created_at=col.created_at, updated_at=col.updated_at,
    )


@router.delete("/{column_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_board_column(
    column_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    await workflow_service.delete_board_column(session, column_id, current_user)


@router.post("/{column_id}/statuses")
async def add_status_to_column(
    column_id: uuid.UUID,
    data: AddStatusToColumn,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    col = await workflow_service.add_status_to_column(session, column_id, data.status_id, current_user)
    return BoardColumnResponse(
        id=col.id, project_id=col.project_id, name=col.name, position=col.position,
        status_ids=col.status_ids, created_at=col.created_at, updated_at=col.updated_at,
    )


@router.delete("/{column_id}/statuses/{status_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_status_from_column(
    column_id: uuid.UUID,
    status_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    await workflow_service.remove_status_from_column(session, column_id, status_id, current_user)
