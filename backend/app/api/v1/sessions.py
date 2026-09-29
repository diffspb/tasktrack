"""Work sessions on tasks (ADR-022, FR-003 TT-12)."""
import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_session
from app.models.user import User
from app.schemas.session import (
    CheckpointCreate, CheckpointResponse, SessionComplete, SessionCreate, SessionRelease, SessionResponse,
)
from app.services import session_service

router = APIRouter(tags=["sessions"])


@router.post("/tasks/{task_id}/sessions", response_model=SessionResponse, status_code=status.HTTP_201_CREATED)
async def claim_task(
    task_id: uuid.UUID,
    data: SessionCreate,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """Start a work session. 409 SESSION_ACTIVE if another executor session holds the task."""
    return await session_service.claim(session, task_id, data, user)


@router.get("/tasks/{task_id}/sessions", response_model=list[SessionResponse])
async def list_task_sessions(
    task_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    return await session_service.list_for_task(session, task_id, user)


@router.get("/sessions/{session_id}", response_model=SessionResponse)
async def get_task_session(
    session_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    return await session_service.get_session_row(session, session_id, user)


@router.post("/sessions/{session_id}/checkpoints", response_model=CheckpointResponse,
             status_code=status.HTTP_201_CREATED)
async def add_checkpoint(
    session_id: uuid.UUID,
    data: CheckpointCreate,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    return await session_service.add_checkpoint(session, session_id, data, user)


@router.post("/sessions/{session_id}/complete", response_model=SessionResponse)
async def complete_session(
    session_id: uuid.UUID,
    data: SessionComplete,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    return await session_service.complete(session, session_id, data, user)


@router.post("/sessions/{session_id}/release", response_model=SessionResponse)
async def release_session(
    session_id: uuid.UUID,
    data: SessionRelease,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """End a session by explicit decision (owner, or manager with a reason)."""
    return await session_service.release(session, session_id, data, user)
