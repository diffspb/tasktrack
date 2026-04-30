import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_session
from app.models.user import User
from app.schemas.decision import (
    DecisionCreate,
    DecisionCriteriaListResponse,
    DecisionCriteriaReplace,
    DecisionResponse,
)
from app.schemas.task import TaskResponse
from app.services import decision_service

router = APIRouter(tags=["decisions"])


@router.get(
    "/tasks/{task_id}/decision-criteria",
    response_model=DecisionCriteriaListResponse,
)
async def get_criteria(
    task_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    items = await decision_service.list_criteria(session, task_id, user)
    return DecisionCriteriaListResponse.model_validate({"items": items})


@router.put(
    "/tasks/{task_id}/decision-criteria",
    response_model=DecisionCriteriaListResponse,
)
async def replace_criteria(
    task_id: uuid.UUID,
    data: DecisionCriteriaReplace,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    items = await decision_service.replace_criteria(session, task_id, data, user)
    return DecisionCriteriaListResponse.model_validate({"items": items})


@router.post(
    "/tasks/{task_id}/decisions",
    response_model=DecisionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def make_decision(
    task_id: uuid.UUID,
    data: DecisionCreate,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    return await decision_service.make_decision(session, task_id, data, user)


@router.get("/tasks/{task_id}/decisions", response_model=DecisionResponse)
async def get_decision(
    task_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    return await decision_service.get_decision(session, task_id, user)


@router.post("/tasks/{task_id}/close", response_model=TaskResponse)
async def close_task(
    task_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    return await decision_service.close_task(session, task_id, user)
