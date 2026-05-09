import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_session
from app.models.user import User
from app.schemas.gantt import GanttChartAddTask, GanttChartCreate, GanttChartResponse, GanttChartUpdate
from app.schemas.task import TaskResponse
from app.services import gantt_service

router = APIRouter(tags=["gantt"])


@router.get("/gantt", response_model=list[GanttChartResponse])
async def list_gantt_charts(
    session: AsyncSession = Depends(get_session),
    _user: User = Depends(get_current_user),
):
    return await gantt_service.list_gantt_charts(session)


@router.post("/gantt", response_model=GanttChartResponse, status_code=status.HTTP_201_CREATED)
async def create_gantt_chart(
    data: GanttChartCreate,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    return await gantt_service.create_gantt_chart(session, data, user)


@router.get("/gantt/{gantt_id}", response_model=GanttChartResponse)
async def get_gantt_chart(
    gantt_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    _user: User = Depends(get_current_user),
):
    return await gantt_service.get_gantt_chart(session, gantt_id)


@router.patch("/gantt/{gantt_id}", response_model=GanttChartResponse)
async def update_gantt_chart(
    gantt_id: uuid.UUID,
    data: GanttChartUpdate,
    session: AsyncSession = Depends(get_session),
    _user: User = Depends(get_current_user),
):
    return await gantt_service.update_gantt_chart(session, gantt_id, data)


@router.delete("/gantt/{gantt_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_gantt_chart(
    gantt_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    _user: User = Depends(get_current_user),
):
    await gantt_service.delete_gantt_chart(session, gantt_id)


@router.get("/gantt/{gantt_id}/tasks", response_model=list[TaskResponse])
async def get_gantt_tasks(
    gantt_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    _user: User = Depends(get_current_user),
):
    return await gantt_service.get_gantt_tasks(session, gantt_id)


@router.post("/gantt/{gantt_id}/tasks", status_code=status.HTTP_204_NO_CONTENT)
async def add_task_to_gantt(
    gantt_id: uuid.UUID,
    data: GanttChartAddTask,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    await gantt_service.add_task_to_gantt(session, gantt_id, data.task_id, user)


@router.delete("/gantt/{gantt_id}/tasks/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_task_from_gantt(
    gantt_id: uuid.UUID,
    task_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    _user: User = Depends(get_current_user),
):
    await gantt_service.remove_task_from_gantt(session, gantt_id, task_id)
