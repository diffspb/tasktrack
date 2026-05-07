import asyncio
import json
import uuid

from fastapi import APIRouter, Depends, status
from fastapi.responses import StreamingResponse
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_session
from app.models.task_type import TaskType
from app.models.user import User
from app.schemas.project import (
    ProjectCreate,
    ProjectMemberAdd,
    ProjectMemberResponse,
    ProjectMembersListResponse,
    ProjectResponse,
    ProjectUpdate,
)
from app.schemas.task_type import TaskTypeResponse
from app.schemas.workflow import SetTaskTypeWorkflow, TaskTypeConfigResponse
from app.core.events import event_bus
from app.services import project_service, workflow_service
from app.services.permissions import require_project_access

router = APIRouter(prefix="/projects", tags=["projects"])


@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project(
    data: ProjectCreate,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    return await project_service.create_project(session, data, user)


@router.get("", response_model=list[ProjectResponse])
async def list_projects(
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    return await project_service.list_projects(session, user)


@router.get("/by-key/{key}", response_model=ProjectResponse)
async def get_project_by_key(
    key: str,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    return await project_service.get_project_by_key(session, key, user)


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    return await project_service.get_project(session, project_id, user)


@router.patch("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: uuid.UUID,
    data: ProjectUpdate,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    return await project_service.update_project(session, project_id, data, user)


@router.post("/{project_id}/archive", response_model=ProjectResponse)
async def archive_project(
    project_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    return await project_service.archive_project(session, project_id, user)


@router.post(
    "/{project_id}/members",
    response_model=ProjectMemberResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_member(
    project_id: uuid.UUID,
    data: ProjectMemberAdd,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    return await project_service.add_member(session, project_id, data, user)


@router.get("/{project_id}/members", response_model=ProjectMembersListResponse)
async def list_members(
    project_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    items = await project_service.list_members(session, project_id, user)
    return {"items": items}


@router.delete("/{project_id}/members/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_member(
    project_id: uuid.UUID,
    user_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    await project_service.remove_member(session, project_id, user_id, user)


# ── Task types ────────────────────────────────────────────────────────────────

@router.get("/{project_id}/task-types")
async def get_project_task_types(
    project_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    await require_project_access(session, project_id, current_user)
    task_types = await session.scalars(
        select(TaskType)
        .where(or_(TaskType.is_system.is_(True), TaskType.project_id == project_id))
        .order_by(TaskType.is_system.desc(), TaskType.name)
    )
    return {"items": [TaskTypeResponse.model_validate(t) for t in task_types]}


# ── Task type configs ─────────────────────────────────────────────────────────

@router.get("/{project_id}/task-type-configs")
async def get_task_type_configs(
    project_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    await require_project_access(session, project_id, current_user)
    items = await workflow_service.get_task_type_configs(session, project_id)
    return {"items": [TaskTypeConfigResponse(**item) for item in items]}


@router.put("/{project_id}/task-type-configs/{task_type_id}")
async def set_task_type_workflow(
    project_id: uuid.UUID,
    task_type_id: uuid.UUID,
    data: SetTaskTypeWorkflow,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    config = await workflow_service.set_task_type_workflow(
        session, project_id, task_type_id, data, current_user
    )
    return config


@router.delete(
    "/{project_id}/task-type-configs/{task_type_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def reset_task_type_workflow(
    project_id: uuid.UUID,
    task_type_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    await workflow_service.reset_task_type_workflow(session, project_id, task_type_id, current_user)


# ── SSE event stream ──────────────────────────────────────────────────────────

@router.get("/{project_id}/events", tags=["events"])
async def project_events(
    project_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    await require_project_access(session, project_id, user)

    async def generate():
        async with event_bus.subscribe(str(project_id)) as queue:
            yield "event: connected\ndata: {}\n\n"
            while True:
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=30.0)
                    yield f"event: {event['type']}\ndata: {json.dumps(event)}\n\n"
                except asyncio.TimeoutError:
                    yield ": keepalive\n\n"
                except asyncio.CancelledError:
                    break

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


