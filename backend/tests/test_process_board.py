"""Задачи-процессы на Kanban-доске (ADR-023, ux-debt 10): при создании первой задачи
процесса статусы его воркфлоу раскладываются по колонкам досок проекта по категории."""
import uuid

from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.bootstrap import ensure_process_types
from app.models.user import User
from app.models.workflow import BoardColumn, BoardColumnStatus, Status, View, ViewType
from app.schemas.project import ProjectCreate
from app.services import project_service


async def _board(client: AsyncClient, db_session: AsyncSession, owner: User):
    project = await project_service.create_project(
        db_session, ProjectCreate(name="PB", key=uuid.uuid4().hex[:8].upper()), owner
    )
    view = await db_session.scalar(select(View).where(View.project_id == project.id, View.type == ViewType.kanban))
    for i, name in enumerate(["To Do", "In Progress", "Review", "Done"]):
        await client.post(f"/api/v1/views/{view.id}/columns", json={"name": name, "position": i})
    return project, view


async def _mapping(db_session: AsyncSession, view_id) -> dict[str, list[str]]:
    rows = (await db_session.execute(
        select(BoardColumn.name, Status.name)
        .join(BoardColumnStatus, BoardColumnStatus.board_column_id == BoardColumn.id)
        .join(Status, Status.id == BoardColumnStatus.status_id)
        .where(BoardColumn.view_id == view_id, Status.workflow_id.isnot(None))
    )).all()
    result: dict[str, list[str]] = {}
    for col, st in rows:
        result.setdefault(col, []).append(st)
    return result


async def test_process_statuses_mapped_by_category(client: AsyncClient, db_session: AsyncSession, stub_user: User):
    await ensure_process_types(db_session)
    project, view = await _board(client, db_session, stub_user)

    r = await client.post(f"/api/v1/projects/{project.id}/tasks", json={"title": "Исследовать", "task_type_key": "research"})
    assert r.status_code == 201
    mapping = await _mapping(db_session, view.id)
    assert "Open" in mapping["To Do"]
    assert "Investigating" in mapping["In Progress"]
    assert "Concluded" in mapping["Done"]

    await client.post(f"/api/v1/projects/{project.id}/tasks", json={"title": "Исполнить", "task_type_key": "execution"})
    mapping = await _mapping(db_session, view.id)
    assert {"In Progress"} <= set(mapping["In Progress"]) and "On Review" in mapping["Review"]


async def test_mapping_is_idempotent_and_keeps_manual_choice(
    client: AsyncClient, db_session: AsyncSession, stub_user: User
):
    await ensure_process_types(db_session)
    project, view = await _board(client, db_session, stub_user)
    await client.post(f"/api/v1/projects/{project.id}/tasks", json={"title": "R1", "task_type_key": "research"})

    # руководитель перенёс статус в другую колонку — повторная раскладка его не трогает
    columns = {c.name: c for c in (await db_session.scalars(select(BoardColumn).where(BoardColumn.view_id == view.id))).all()}
    investigating = await db_session.scalar(select(Status).where(Status.name == "Investigating"))
    await client.delete(f"/api/v1/board-columns/{columns['In Progress'].id}/statuses/{investigating.id}")
    await client.post(f"/api/v1/board-columns/{columns['Review'].id}/statuses", json={"status_id": str(investigating.id)})

    await client.post(f"/api/v1/projects/{project.id}/tasks", json={"title": "R2", "task_type_key": "research"})
    mapping = await _mapping(db_session, view.id)
    assert "Investigating" in mapping["Review"] and "Investigating" not in mapping.get("In Progress", [])
    assert mapping["To Do"].count("Open") == 1


async def test_board_without_columns_untouched(client: AsyncClient, db_session: AsyncSession, stub_user: User):
    await ensure_process_types(db_session)
    project = await project_service.create_project(
        db_session, ProjectCreate(name="PB2", key=uuid.uuid4().hex[:8].upper()), stub_user
    )
    r = await client.post(f"/api/v1/projects/{project.id}/tasks", json={"title": "R", "task_type_key": "research"})
    assert r.status_code == 201


async def test_project_workflows_can_include_used_process_workflows(
    client: AsyncClient, db_session: AsyncSession, stub_user: User
):
    await ensure_process_types(db_session)
    project, _ = await _board(client, db_session, stub_user)
    url = f"/api/v1/projects/{project.id}/workflows"
    assert [w["name"] for w in (await client.get(url)).json()] == ["Basic"]
    assert [w["name"] for w in (await client.get(url, params={"include_used_system": True})).json()] == ["Basic"]

    await client.post(f"/api/v1/projects/{project.id}/tasks", json={"title": "R", "task_type_key": "research"})
    names = [w["name"] for w in (await client.get(url, params={"include_used_system": True})).json()]
    assert names == ["Basic", "Исследование"]
    assert [w["name"] for w in (await client.get(url)).json()] == ["Basic"]  # редакторы видят только свои

