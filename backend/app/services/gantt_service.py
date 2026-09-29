import uuid

from fastapi import HTTPException, status
from sqlalchemy import and_, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.gantt import GanttChart, GanttChartTask
from app.models.task import Task, TaskLink
from app.models.user import User
from app.schemas.gantt import GanttChartCreate, GanttChartUpdate
from app.services import audit_service
from app.services.permissions import require_project_access, visible_project_ids

_GANTT = ("name", "description", "position")


async def _audit(session: AsyncSession, user: User, gantt_id: uuid.UUID, action: str,
                 before: dict | None = None, after: dict | None = None) -> None:
    """Gantt charts belong to no project: their events are system-level (ADR-018)."""
    await audit_service.record(
        session, actor_id=user.id, project_id=None, entity_type="gantt_chart",
        entity_id=gantt_id, action=action, before=before, after=after,
    )


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


async def _get_own_gantt_chart(
    session: AsyncSession, gantt_id: uuid.UUID, user: User
) -> GanttChart:
    """Charts are visible to everyone (ADR-012); only the owner or a superuser changes one."""
    gantt = await get_gantt_chart(session, gantt_id)
    if gantt.owner_id != user.id and not user.is_superuser:
        raise HTTPException(status.HTTP_403_FORBIDDEN, {"code": "PERMISSION_DENIED"})
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
    await session.flush()
    await _audit(session, user, gantt.id, "created", after=audit_service.snapshot(gantt, _GANTT))
    await session.commit()
    await session.refresh(gantt)
    return gantt


async def update_gantt_chart(
    session: AsyncSession, gantt_id: uuid.UUID, data: GanttChartUpdate, user: User
) -> GanttChart:
    gantt = await _get_own_gantt_chart(session, gantt_id, user)
    before = audit_service.snapshot(gantt, _GANTT)
    if data.name is not None:
        gantt.name = data.name
    if data.description is not None:
        gantt.description = data.description
    if data.settings is not None:
        gantt.settings = {**gantt.settings, **data.settings}
    if data.position is not None:
        gantt.position = data.position
    await _audit(session, user, gantt.id, "updated",
                 *audit_service.diff(before, audit_service.snapshot(gantt, _GANTT)))
    await session.commit()
    await session.refresh(gantt)
    return gantt


async def delete_gantt_chart(session: AsyncSession, gantt_id: uuid.UUID, user: User) -> None:
    gantt = await _get_own_gantt_chart(session, gantt_id, user)
    await _audit(session, user, gantt.id, "deleted", before=audit_service.snapshot(gantt, _GANTT))
    await session.delete(gantt)
    await session.commit()


async def add_task_to_gantt(
    session: AsyncSession, gantt_id: uuid.UUID, task_id: uuid.UUID, user: User
) -> None:
    await _get_own_gantt_chart(session, gantt_id, user)

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
    await _audit(session, user, gantt_id, "task_added", after={"task_id": str(task_id)})
    await session.commit()


async def remove_task_from_gantt(
    session: AsyncSession, gantt_id: uuid.UUID, task_id: uuid.UUID, user: User
) -> None:
    await _get_own_gantt_chart(session, gantt_id, user)
    entry = await session.scalar(
        select(GanttChartTask).where(
            GanttChartTask.gantt_id == gantt_id,
            GanttChartTask.task_id == task_id,
        )
    )
    if not entry:
        raise HTTPException(status.HTTP_404_NOT_FOUND, {"code": "GANTT_TASK_NOT_FOUND"})
    await _audit(session, user, gantt_id, "task_removed", before={"task_id": str(task_id)})
    await session.delete(entry)
    await session.commit()


async def get_gantt_tasks(
    session: AsyncSession, gantt_id: uuid.UUID, user: User
) -> list[Task]:
    """Return root tasks in the gantt + all their descendants (recursive CTE),
    limited to projects the user can see."""
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

    pos_rows = await session.execute(
        select(GanttChartTask.task_id, GanttChartTask.position)
        .where(GanttChartTask.gantt_id == gantt_id)
    )
    pos_map = {row[0]: row[1] for row in pos_rows}

    task_list = list((await session.scalars(
        select(Task)
        .options(selectinload(Task.task_type))
        .where(Task.id.in_(task_ids), Task.project_id.in_(visible_project_ids(user)))
    )).all())
    # Root tasks sorted by their position in gantt_chart_tasks; subtasks by created_at
    task_list.sort(key=lambda t: (pos_map.get(t.id, 999_999), t.created_at))
    return task_list


async def reorder_gantt_tasks(
    session: AsyncSession, gantt_id: uuid.UUID, task_ids: list[uuid.UUID], user: User
) -> None:
    await _get_own_gantt_chart(session, gantt_id, user)
    for idx, task_id in enumerate(task_ids):
        entry = await session.scalar(
            select(GanttChartTask).where(
                GanttChartTask.gantt_id == gantt_id,
                GanttChartTask.task_id == task_id,
            )
        )
        if entry:
            entry.position = idx + 1
    await _audit(session, user, gantt_id, "reordered", after={"task_ids": [str(t) for t in task_ids]})
    await session.commit()


async def get_gantt_links(
    session: AsyncSession, gantt_id: uuid.UUID, user: User
) -> list[TaskLink]:
    """Return all TaskLinks where both source and target are in the gantt's task tree
    and in projects the user can see."""
    await get_gantt_chart(session, gantt_id)

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

    task_ids = list((await session.scalars(
        select(Task.id).where(Task.id.in_(task_ids), Task.project_id.in_(visible_project_ids(user)))
    )).all())
    if not task_ids:
        return []

    links = await session.scalars(
        select(TaskLink)
        .options(
            selectinload(TaskLink.link_type),
            selectinload(TaskLink.source_task).selectinload(Task.task_type),
            selectinload(TaskLink.target_task).selectinload(Task.task_type),
        )
        .where(
            and_(
                TaskLink.source_task_id.in_(task_ids),
                TaskLink.target_task_id.in_(task_ids),
            )
        )
        .order_by(TaskLink.created_at)
    )
    return list(links.all())
