import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_session
from app.models.user import User
from app.schemas.decision import (
    RevisionRequest,
    SolutionCreate,
    SolutionResponse,
    SolutionTransitionResponse,
    SolutionUpdate,
)
from app.services import decision_service

router = APIRouter(tags=["solutions"])


@router.post(
    "/assignments/{assignment_id}/solution",
    response_model=SolutionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_solution(
    assignment_id: uuid.UUID,
    data: SolutionCreate,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    return await decision_service.create_solution(session, assignment_id, data, user)


@router.get(
    "/assignments/{assignment_id}/solution",
    response_model=SolutionResponse,
)
async def get_solution(
    assignment_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    return await decision_service.get_solution_by_assignment(session, assignment_id, user)


@router.patch("/solutions/{solution_id}", response_model=SolutionResponse)
async def update_solution(
    solution_id: uuid.UUID,
    data: SolutionUpdate,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    return await decision_service.update_solution(session, solution_id, data, user)


@router.post("/solutions/{solution_id}/submit", response_model=SolutionTransitionResponse)
async def submit_solution(
    solution_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    sol, transitioned = await decision_service.submit_solution(session, solution_id, user)
    return SolutionTransitionResponse(
        id=sol.id,
        status=sol.status,
        submitted_at=sol.submitted_at,
        revision_comment=sol.revision_comment,
        task_transitioned_to=transitioned,
    )


@router.post("/solutions/{solution_id}/withdraw", response_model=SolutionTransitionResponse)
async def withdraw_solution(
    solution_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    sol, transitioned = await decision_service.withdraw_solution(session, solution_id, user)
    return SolutionTransitionResponse(
        id=sol.id,
        status=sol.status,
        submitted_at=sol.submitted_at,
        revision_comment=sol.revision_comment,
        task_transitioned_to=transitioned,
    )


@router.post(
    "/solutions/{solution_id}/request-revision",
    response_model=SolutionTransitionResponse,
)
async def request_revision(
    solution_id: uuid.UUID,
    data: RevisionRequest,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    sol, transitioned = await decision_service.request_revision(
        session, solution_id, data.feedback, user
    )
    return SolutionTransitionResponse(
        id=sol.id,
        status=sol.status,
        submitted_at=sol.submitted_at,
        revision_comment=sol.revision_comment,
        task_transitioned_to=transitioned,
    )


@router.get(
    "/tasks/{task_id}/solutions",
    response_model=list[SolutionResponse],
)
async def list_task_solutions(
    task_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    return await decision_service.list_task_solutions(session, task_id, user)
