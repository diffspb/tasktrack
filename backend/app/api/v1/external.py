"""External registry (ADR-024, contract tasktrack-external-v1): providers, facts, snapshots.

Registering providers and aliases — superuser. Importing facts and snapshots — superuser or
a manager of the project named in `project_id`. The same rules apply to a future adapter.
"""
import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_session
from app.models.user import User
from app.schemas.external import (
    AliasCreate, EventResponse, FactImport, FactImportResult, ObjectDetail, ObjectRef, ObjectType,
    ProviderCreate, ProviderResponse, ProviderUpdate, SnapshotImport, SnapshotResponse,
)
from app.services import external_service

router = APIRouter(prefix="/external", tags=["external"])


@router.get("/providers", response_model=list[ProviderResponse])
async def list_providers(
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    return await external_service.list_providers(session)


@router.post("/providers", response_model=ProviderResponse, status_code=status.HTTP_201_CREATED)
async def create_provider(
    data: ProviderCreate,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    return await external_service.create_provider(session, data, user)


@router.patch("/providers/{provider_id}", response_model=ProviderResponse)
async def update_provider(
    provider_id: uuid.UUID,
    data: ProviderUpdate,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    return await external_service.update_provider(session, provider_id, data, user)


@router.get("/providers/{key}/events", response_model=list[EventResponse])
async def list_events(
    key: str,
    limit: int = Query(100, ge=1, le=1000),
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    return await external_service.list_events(session, key, user, limit)


@router.post("/facts", response_model=FactImportResult)
async def import_fact(
    data: FactImport,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """Registers a pinned revision / fact. With event_id a repeat is confirmed without a second
    mutation; other content under the same event_id is EVENT_CONFLICT."""
    return await external_service.import_fact(session, data, user)


@router.post("/snapshots", response_model=SnapshotResponse)
async def import_snapshot(
    data: SnapshotImport,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    return await external_service.import_snapshot(session, data, user)


@router.post("/aliases", response_model=ObjectDetail, status_code=status.HTTP_201_CREATED)
async def create_alias(
    data: AliasCreate,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    return await external_service.create_alias(session, data, user)


@router.get("/objects", response_model=ObjectDetail)
async def get_object(
    provider: str,
    namespace: str,
    type: ObjectType,
    id: str,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    return await external_service.object_detail(
        session, ObjectRef(provider=provider, namespace=namespace, type=type, id=id)
    )
