"""Task assignment (WorkPackage) — ADR-020, FR-003 TT-09."""
import uuid
from typing import Literal

import yaml
from fastapi import APIRouter, Depends, Query, status
from fastapi.responses import JSONResponse, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_session
from app.models.user import User
from app.schemas.work_package import WorkPackageContent, WorkPackageResponse, WorkPackageState
from app.services import work_package_service

router = APIRouter(tags=["work-packages"])


@router.get("/tasks/{task_id}/work-package", response_model=WorkPackageState)
async def get_work_package_state(
    task_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    return await work_package_service.get_state(session, task_id, user)


@router.put("/tasks/{task_id}/work-package/draft", response_model=WorkPackageState)
async def save_work_package_draft(
    task_id: uuid.UUID,
    data: WorkPackageContent,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    return await work_package_service.save_draft(session, task_id, data, user)


@router.post(
    "/tasks/{task_id}/work-package/issue",
    response_model=WorkPackageResponse, status_code=status.HTTP_201_CREATED,
)
async def issue_work_package(
    task_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    return await work_package_service.issue(session, task_id, user)


@router.get("/tasks/{task_id}/work-packages", response_model=list[WorkPackageResponse])
async def list_work_packages(
    task_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    return await work_package_service.list_versions(session, task_id, user)


@router.get("/work-packages/{package_id}", response_model=WorkPackageResponse)
async def get_work_package(
    package_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    return await work_package_service.get_package(session, package_id, user)


@router.get("/work-packages/{package_id}/export")
async def export_work_package(
    package_id: uuid.UUID,
    format: Literal["json", "yaml"] = Query("json"),
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """Pinned copy for console agents: id, version and digest travel with the content."""
    data = await work_package_service.export(session, package_id, user)
    filename = f"{data['task']['key']}-v{data['version']}"
    if format == "yaml":
        return Response(
            content=yaml.safe_dump(data, allow_unicode=True, sort_keys=False),
            media_type="application/yaml",
            headers={"Content-Disposition": f'inline; filename="{filename}.yaml"'},
        )
    return JSONResponse(data, headers={"Content-Disposition": f'inline; filename="{filename}.json"'})
