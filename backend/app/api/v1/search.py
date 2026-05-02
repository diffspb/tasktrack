import uuid

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_session
from app.models.user import User
from app.services import search_service

router = APIRouter(tags=["search"])


class SearchProjectRef(BaseModel):
    id: uuid.UUID
    key: str
    name: str


class SearchHit(BaseModel):
    id: uuid.UUID
    key: str
    title: str
    current_status_id: str
    project: SearchProjectRef
    highlight: str


class SearchResponse(BaseModel):
    items: list[SearchHit]


@router.get("/search", response_model=SearchResponse)
async def search(
    q: str = Query(default="", min_length=0),
    project_id: uuid.UUID | None = None,
    limit: int = Query(default=20, le=50),
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    items = await search_service.search_tasks(
        session, q=q, user=user, project_id=project_id, limit=limit,
    )
    return {"items": items}
