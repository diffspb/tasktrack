import uuid

from fastapi import HTTPException, status
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.gantt import GanttChart, GanttChartTask
from app.models.task import Task
from app.models.user import User
from app.schemas.gantt import GanttChartCreate, GanttChartUpdate
from app.services.permissions import require_project_access


async def list_gantt_charts(session: AsyncSession) -> list[GanttChart]:
    result = await session.scalars(
        select(GanttChart).order_by(GanttChart.position, GanttChart.created_at)
    )
    return list(result.all())


async def get_gantt_chart(session: AsyncSession, gantt_id: uuid.UUID) -> GanttChart:
    gantt = await session.get(GanttChart, gantt_id)
    if not gantt:
        raise HTTPException(status.HTTP_404_NOT_FOUND, {"code": "GANTT_NOT_FOUND"})
    return gantt


async def create_gantt_chart(
    session: AsyncSession, data: GanttChartCreate, user: User
) -> GanttChart:
    max_pos = await session.scalar(
        select(GanttChart.position).order_by(GanttChart.position.desc()).limit(1)
    )
    gantt = GanttChart(
        owner_id=user.id,
        name=data.name,
        description=data.description,
        settings={},
        position=(max_pos or 0) + 1,
    )
    session.add(gantt)
    await session.commit()
    await session.refresh(gantt)
    return gantt


async def update_gantt_chart(
    session: AsyncSession, gantt_id: uuid.UUID, data: GanttChartUpdate
) -> GanttChart:
    gantt = await get_gantt_chart(session, gantt_id)
    if data.name is not None:
        gantt.name = data.name
    if data.description is not None:
        gantt.description = data.description
    if data.settings is not None:
        gantt.settings = {**gantt.settings, **data.settings}
    if data.position is not None:
        gantt.position = data.position
    await session.commit()
    await session.refresh(gantt)
    return gantt


async def delete_gantt_chart(session: AsyncSession, gantt_id: uuid.UUID) -> None:
    gantt = await get_gantt_chart(session, gantt_id)
    await session.delete(gantt)
    await session.commit()


async def add_task_to_gantt(
    session: AsyncSession, gantt_id: uuid.UUID, task_id: uuid.UUID, user: User
) -> None:
    await get_gantt_chart(session, gantt_id)

    task = await session.get(Task, task_id)
    if not task or task.deleted_at is not None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, {"code": "TASK_NOT_FOUND"})

    await require_project_access(session, task.project_id, user)

    existing = await session.scalar(
        select(GanttChartTask).where(
            GanttChartTask.gantt_id == gantt_id,
            GanttChartTask.task_id == task_id,
        )
    )
    if existing:
        return

    max_pos = await session.scalar(
        select(GanttChartTask.position)
        .where(GanttChartTask.gantt_id == gantt_id)
        .order_by(GanttChartTask.position.desc())
        .limit(1)
    )
    entry = GanttChartTask(
        gantt_id=gantt_id, task_id=task_id, position=(max_pos or 0) + 1
    )
    session.add(entry)
    await session.commit()


async def remove_task_from_gantt(
    session: AsyncSession, gantt_id: uuid.UUID, task_id: uuid.UUID
) -> None:
    await get_gantt_chart(session, gantt_id)
    entry = await session.scalar(
        select(GanttChartTask).where(
            GanttChartTask.gantt_id == gantt_id,
            GanttChartTask.task_id == task_id,
        )
    )
    if not entry:
        raise HTTPException(status.HTTP_404_NOT_FOUND, {"code": "GANTT_TASK_NOT_FOUND"})
    await session.delete(entry)
    await session.commit()


async def get_gantt_tasks(
    session: AsyncSession, gantt_id: uuid.UUID
) -> list[Task]:
    """Return root tasks in the gantt + all their descendants (recursive CTE)."""
    await get_gantt_chart(session, gantt_id)

    # Recursive CTE: root tasks from gantt_chart_tasks + all descendants
    cte_sql = text("""
        WITH RECURSIVE gantt_tree AS (
            SELECT t.id
            FROM tasks t
            JOIN gantt_chart_tasks gct ON gct.task_id = t.id
            WHERE gct.gantt_id = :gantt_id AND t.deleted_at IS NULL

            UNION

            SELECT t.id
            FROM tasks t
            JOIN gantt_tree g ON t.parent_task_id = g.id
            WHERE t.deleted_at IS NULL
        )
        SELECT id FROM gantt_tree
    """)
    ids_result = await session.execute(cte_sql, {"gantt_id": str(gantt_id)})
    task_ids = [row[0] for row in ids_result]

    if not task_ids:
        return []

    tasks = await session.scalars(
        select(Task)
        .options(selectinload(Task.task_type))
        .where(Task.id.in_(task_ids))
        .order_by(Task.parent_task_id.nulls_first(), Task.created_at)
    )
    return list(tasks.all())
