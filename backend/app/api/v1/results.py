"""Result proposals, reviews, delivery and the reviewer profile (ADR-021, ADR-024, FR-003 TT-14–17, TT-21)."""
import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_session
from app.models.user import User
from app.schemas.external import AcceptanceWithdraw, DeliveriesView, RecipientAcceptanceResponse
from app.schemas.project import ProjectMemberResponse
from app.schemas.result import (
    DeliveryCreate, MemberUpdate, ProposalCreate, ProposalResponse,
    RecipientAcceptanceCreate, ReviewCreate, ReviewQueueItem, ReviewResponse,
)
from app.schemas.task import TaskResponse
from app.services import result_service

router = APIRouter(tags=["results"])


@router.post("/tasks/{task_id}/proposals", response_model=ProposalResponse, status_code=status.HTTP_201_CREATED)
async def submit_proposal(
    task_id: uuid.UUID,
    data: ProposalCreate,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    return await result_service.submit_proposal(session, task_id, data, user)


@router.get("/tasks/{task_id}/proposals", response_model=list[ProposalResponse])
async def list_proposals(
    task_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    return await result_service.list_proposals(session, task_id, user)


@router.get("/proposals/{proposal_id}", response_model=ProposalResponse)
async def get_proposal(
    proposal_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    return await result_service.get_proposal(session, proposal_id, user)


@router.post("/proposals/{proposal_id}/withdraw", response_model=ProposalResponse)
async def withdraw_proposal(
    proposal_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    return await result_service.withdraw_proposal(session, proposal_id, user)


@router.post("/proposals/{proposal_id}/reviews", response_model=ReviewResponse, status_code=status.HTTP_201_CREATED)
async def review_proposal(
    proposal_id: uuid.UUID,
    data: ReviewCreate,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    return await result_service.review_proposal(session, proposal_id, data, user)


@router.get("/review-queue", response_model=list[ReviewQueueItem])
async def review_queue(
    project_id: uuid.UUID | None = None,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """Proposals waiting for the caller's review (FR-003 TT-22)."""
    return await result_service.review_queue(session, user, project_id=project_id)


@router.post("/tasks/{task_id}/delivery", response_model=TaskResponse)
async def propose_delivery(
    task_id: uuid.UUID,
    data: DeliveryCreate,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    return await result_service.propose_delivery(session, task_id, data, user)


@router.post("/tasks/{task_id}/recipient-acceptance", response_model=TaskResponse)
async def record_recipient_acceptance(
    task_id: uuid.UUID,
    data: RecipientAcceptanceCreate,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    return await result_service.record_recipient_acceptance(session, task_id, data, user)


@router.get("/tasks/{task_id}/deliveries", response_model=DeliveriesView)
async def list_deliveries(
    task_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """Deliveries with their bound acceptances; manual records without a binding are historical."""
    return await result_service.list_deliveries(session, task_id, user)


@router.post("/recipient-acceptances/{acceptance_id}/withdraw", response_model=RecipientAcceptanceResponse)
async def withdraw_recipient_acceptance(
    acceptance_id: uuid.UUID,
    data: AcceptanceWithdraw,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    return await result_service.withdraw_recipient_acceptance(session, acceptance_id, data.reason, user)


@router.patch("/projects/{project_id}/members/{user_id}", response_model=ProjectMemberResponse)
async def update_member(
    project_id: uuid.UUID,
    user_id: uuid.UUID,
    data: MemberUpdate,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """Change a member's role or reviewer profile (manager/admin)."""
    return await result_service.update_member(session, project_id, user_id, data, user)
