import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.bootstrap import ensure_system_data
from app.core.db import get_session
from app.models.user import User
from app.schemas.api_key import (
    ApiKeyCreate, ApiKeyIssued, ApiKeyResponse,
    ServiceAccountCreate, ServiceAccountResponse, ServiceAccountUpdate,
)
from app.services import api_key_service

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/system-status")
async def system_status(
    session: AsyncSession = Depends(get_session),
    _: User = Depends(get_current_user),
):
    from app.models.task_type import TaskType

    count = await session.scalar(
        select(func.count()).select_from(TaskType).where(TaskType.is_system.is_(True))
    )
    return {"initialized": bool(count)}


@router.post("/initialize")
async def initialize_system(
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    if not user.is_superuser:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail={"code": "PERMISSION_DENIED"})
    await ensure_system_data()
    return {"ok": True}


# ── Service accounts and API keys (ADR-017, FR-003 TT-05) ─────────────────────

def _require_superuser(user: User = Depends(get_current_user)) -> User:
    if not user.is_superuser:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail={"code": "PERMISSION_DENIED"})
    return user


def _issued(key, token: str) -> ApiKeyIssued:
    return ApiKeyIssued(**ApiKeyResponse.model_validate(key).model_dump(), token=token)


@router.post(
    "/service-accounts", response_model=ServiceAccountResponse, status_code=status.HTTP_201_CREATED
)
async def create_service_account(
    data: ServiceAccountCreate,
    session: AsyncSession = Depends(get_session),
    admin: User = Depends(_require_superuser),
):
    return await api_key_service.create_service_account(
        session, data.email, data.display_name, actor_id=admin.id
    )


@router.get("/service-accounts", response_model=list[ServiceAccountResponse])
async def list_service_accounts(
    session: AsyncSession = Depends(get_session),
    _: User = Depends(_require_superuser),
):
    return await api_key_service.list_service_accounts(session)


@router.patch("/service-accounts/{user_id}", response_model=ServiceAccountResponse)
async def update_service_account(
    user_id: uuid.UUID,
    data: ServiceAccountUpdate,
    session: AsyncSession = Depends(get_session),
    admin: User = Depends(_require_superuser),
):
    return await api_key_service.set_service_account_active(
        session, user_id, data.is_active, actor_id=admin.id
    )


@router.post(
    "/service-accounts/{user_id}/api-keys",
    response_model=ApiKeyIssued, status_code=status.HTTP_201_CREATED,
)
async def issue_api_key(
    user_id: uuid.UUID,
    data: ApiKeyCreate,
    session: AsyncSession = Depends(get_session),
    admin: User = Depends(_require_superuser),
):
    key, token = await api_key_service.issue_key(
        session, user_id, data.name, expires_at=data.expires_at, created_by=admin.id
    )
    return _issued(key, token)


@router.get("/service-accounts/{user_id}/api-keys", response_model=list[ApiKeyResponse])
async def list_api_keys(
    user_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    _: User = Depends(_require_superuser),
):
    return await api_key_service.list_keys(session, user_id)


@router.delete("/api-keys/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_api_key(
    key_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    admin: User = Depends(_require_superuser),
):
    await api_key_service.revoke_key(session, key_id, actor_id=admin.id)


@router.post(
    "/api-keys/{key_id}/rotate", response_model=ApiKeyIssued, status_code=status.HTTP_201_CREATED
)
async def rotate_api_key(
    key_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    admin: User = Depends(_require_superuser),
):
    key, token = await api_key_service.rotate_key(session, key_id, created_by=admin.id)
    return _issued(key, token)
