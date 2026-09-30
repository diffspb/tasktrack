"""Portfolio mode (ADR-024, FR-003 TT-08/10/11/19/20): project link, task bases, readiness,
blockers, impact assessment and work proposals."""
import uuid

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_session
from app.models.user import User
from app.schemas.external import (
    BasisCreate, BasisResponse, BlockerCreate, BlockerResolve, BlockerResponse, ImpactDecision,
    ImpactResponse, PortfolioLinkResponse, PortfolioLinkSet, Readiness, WorkProposalDecide,
    WorkProposalImport, WorkProposalImportResult, WorkProposalResponse,
)
from app.services import portfolio_service, work_proposal_service

router = APIRouter(tags=["portfolio"])


# ── TT-08 ────────────────────────────────────────────────────────────────────

@router.get("/projects/{project_id}/portfolio", response_model=PortfolioLinkResponse | None)
async def get_portfolio_link(
    project_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """null — a standalone project: external checks do not apply."""
    return await portfolio_service.get_project_link(session, project_id, user)


@router.put("/projects/{project_id}/portfolio", response_model=PortfolioLinkResponse)
async def set_portfolio_link(
    project_id: uuid.UUID,
    data: PortfolioLinkSet,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    return await portfolio_service.set_link(session, project_id, data, user)


@router.delete("/projects/{project_id}/portfolio", status_code=status.HTTP_204_NO_CONTENT)
async def remove_portfolio_link(
    project_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    await portfolio_service.remove_link(session, project_id, user)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ── TT-10 / TT-11 ────────────────────────────────────────────────────────────

@router.get("/tasks/{task_id}/bases", response_model=list[BasisResponse])
async def list_bases(
    task_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    return await portfolio_service.list_bases(session, task_id, user)


@router.post("/tasks/{task_id}/bases", response_model=BasisResponse, status_code=status.HTTP_201_CREATED)
async def add_basis(
    task_id: uuid.UUID,
    data: BasisCreate,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    return await portfolio_service.add_basis(session, task_id, data, user)


@router.delete("/bases/{basis_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_basis(
    basis_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    await portfolio_service.remove_basis(session, basis_id, user)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/tasks/{task_id}/readiness", response_model=Readiness)
async def get_readiness(
    task_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """Five conditions of contract v1.0 with reasons, facts and the date of the information."""
    return await portfolio_service.task_readiness(session, task_id, user)


@router.get("/tasks/{task_id}/blockers", response_model=list[BlockerResponse])
async def list_blockers(
    task_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    return await portfolio_service.list_blockers(session, task_id, user)


@router.post("/tasks/{task_id}/blockers", response_model=BlockerResponse, status_code=status.HTTP_201_CREATED)
async def add_blocker(
    task_id: uuid.UUID,
    data: BlockerCreate,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    return await portfolio_service.add_blocker(session, task_id, data, user)


@router.post("/blockers/{blocker_id}/resolve", response_model=BlockerResponse)
async def resolve_blocker(
    blocker_id: uuid.UUID,
    data: BlockerResolve,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    return await portfolio_service.resolve_blocker(session, blocker_id, data, user)


@router.get("/tasks/{task_id}/impact-assessments", response_model=list[ImpactResponse])
async def list_impact_assessments(
    task_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    return await portfolio_service.list_assessments(session, task_id, user)


@router.post("/impact-assessments/{assessment_id}/decide", response_model=ImpactResponse)
async def decide_impact(
    assessment_id: uuid.UUID,
    data: ImpactDecision,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    return await portfolio_service.decide_assessment(session, assessment_id, data, user)


# ── TT-19 / TT-20 ────────────────────────────────────────────────────────────

@router.get("/projects/{project_id}/work-proposals", response_model=list[WorkProposalResponse])
async def list_work_proposals(
    project_id: uuid.UUID,
    status_filter: str | None = Query(None, alias="status"),
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    return await work_proposal_service.list_proposals(session, project_id, user, status_filter)


@router.post("/projects/{project_id}/work-proposals", response_model=WorkProposalImportResult)
async def import_work_proposal(
    project_id: uuid.UUID,
    data: WorkProposalImport,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """Import never creates a task ready for execution; a repeat or a new revision of the
    basis never creates a second proposal."""
    return await work_proposal_service.import_proposal(session, project_id, data, user)


@router.get("/work-proposals/{proposal_id}", response_model=WorkProposalResponse)
async def get_work_proposal(
    proposal_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    return await work_proposal_service.get_proposal(session, proposal_id, user)


@router.post("/work-proposals/{proposal_id}/decide", response_model=WorkProposalResponse)
async def decide_work_proposal(
    proposal_id: uuid.UUID,
    data: WorkProposalDecide,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    return await work_proposal_service.decide(session, proposal_id, data, user)
