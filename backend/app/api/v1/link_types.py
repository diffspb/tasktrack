from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_session as get_db
from app.models.user import User
from app.schemas.link_type import LinkTypeCreate, LinkTypeUpdate, LinkTypeResponse
from app.services import link_type_service

router = APIRouter(prefix="/link-types", tags=["link-types"])


@router.get("", response_model=list[LinkTypeResponse])
async def list_link_types(
    include_inactive: bool = Query(False),
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    return await link_type_service.list_link_types(db, include_inactive=include_inactive)


@router.post("", response_model=LinkTypeResponse, status_code=201)
async def create_link_type(
    data: LinkTypeCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return await link_type_service.create_link_type(db, data, user)


@router.patch("/{link_type_id}", response_model=LinkTypeResponse)
async def update_link_type(
    link_type_id: UUID,
    data: LinkTypeUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return await link_type_service.update_link_type(db, link_type_id, data, user)


@router.delete("/{link_type_id}", status_code=204)
async def delete_link_type(
    link_type_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    await link_type_service.delete_link_type(db, link_type_id, user)
