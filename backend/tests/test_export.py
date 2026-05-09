"""Tests for project export / import."""
import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.link_type import LinkType
from app.models.user import User
from app.schemas.project import ProjectCreate
from app.schemas.task import TaskCreate, TaskLinkCreate
from app.services import project_export_service, project_service, task_service
from app.services.task_link_service import create_task_link


# ─────────────────────────── helpers ─────────────────────────────────────────


def _unique_key() -> str:
    return uuid.uuid4().hex[:8].upper()


async def _ensure_link_type(session: AsyncSession) -> LinkType:
    """Return the 'blocks' link type, creating it if not seeded in the test DB."""
    lt = await session.scalar(
        select(LinkType).where(LinkType.name == "blocks", LinkType.is_active.is_(True))
    )
    if lt is None:
        lt = LinkType(
            name="blocks",
            outward_name="blocks",
            inward_name="is blocked by",
            is_directed=True,
            color="#ef4444",
            constraint={"type": "blocking"},
            position=0,
            is_active=True,
        )
        session.add(lt)
        await session.flush()
    return lt


async def _setup(session: AsyncSession, user: User):
    """Create a project with 3 tasks, 1 link, and 1 comment for tests."""
    p = await project_service.create_project(
        session, ProjectCreate(name="Export Test", key=_unique_key()), user,
    )
    t1 = await task_service.create_task(
        session, p.id,
        TaskCreate(title="Alpha", description="First task", priority="high"),
        user,
    )
    t2 = await task_service.create_task(
        session, p.id,
        TaskCreate(title="Beta", task_type_key="bug"),
        user,
    )
    t3 = await task_service.create_task(
        session, p.id,
        TaskCreate(title="Gamma subtask", parent_task_id=t1.id),
        user,
    )

    # Create a link between t1 and t2
    lt = await _ensure_link_type(session)
    await create_task_link(
        session, t1.id,
        TaskLinkCreate(target_task_id=t2.id, link_type_id=lt.id),
        user,
    )

    return p, t1, t2, t3


# ─────────────────────────── export tests ────────────────────────────────────


async def test_export_structure(db_session: AsyncSession, stub_user: User):
    p, t1, t2, t3 = await _setup(db_session, stub_user)

    data = await project_export_service.export_project(db_session, p.id, stub_user)

    assert data["version"] == 1
    assert "exported_at" in data

    proj = data["project"]
    assert proj["name"] == "Export Test"
    assert proj["key"] == p.key

    assert len(data["workflows"]) >= 1
    wf = data["workflows"][0]
    assert len(wf["statuses"]) >= 1
    assert any(s["is_default"] for s in wf["statuses"])

    tasks_out = data["tasks"]
    assert len(tasks_out) == 3
    titles = {t["title"] for t in tasks_out}
    assert {"Alpha", "Beta", "Gamma subtask"} == titles


async def test_export_parent_task_key(db_session: AsyncSession, stub_user: User):
    p, t1, t2, t3 = await _setup(db_session, stub_user)
    data = await project_export_service.export_project(db_session, p.id, stub_user)

    gamma = next(t for t in data["tasks"] if t["title"] == "Gamma subtask")
    alpha = next(t for t in data["tasks"] if t["title"] == "Alpha")
    assert gamma["parent_task_key"] == alpha["key"]


async def test_export_links(db_session: AsyncSession, stub_user: User):
    p, t1, t2, t3 = await _setup(db_session, stub_user)
    data = await project_export_service.export_project(db_session, p.id, stub_user)

    alpha_key = next(t["key"] for t in data["tasks"] if t["title"] == "Alpha")
    beta_key = next(t["key"] for t in data["tasks"] if t["title"] == "Beta")

    assert any(
        lnk["source_task_key"] == alpha_key
        and lnk["target_task_key"] == beta_key
        and lnk["link_type_name"] == "blocks"
        for lnk in data["links"]
    )


async def test_export_http(client: AsyncClient, db_session: AsyncSession, stub_user: User):
    p, *_ = await _setup(db_session, stub_user)
    resp = await client.get(f"/api/v1/projects/{p.id}/export")
    assert resp.status_code == 200
    assert "attachment" in resp.headers.get("content-disposition", "")
    data = resp.json()
    assert data["project"]["key"] == p.key


# ─────────────────────────── import tests ────────────────────────────────────


async def test_import_roundtrip(db_session: AsyncSession, stub_user: User):
    p, t1, t2, t3 = await _setup(db_session, stub_user)
    export_data = await project_export_service.export_project(db_session, p.id, stub_user)

    new_key = _unique_key()
    imported = await project_export_service.import_project(
        db_session, export_data, new_key,
        include_comments=True, reset_statuses=False, user=stub_user,
    )

    assert imported.key == new_key
    assert imported.name == "Export Test"

    # All 3 tasks should exist
    from sqlalchemy import select
    from app.models.task import Task
    imported_tasks = list((await db_session.scalars(
        select(Task).where(Task.project_id == imported.id, Task.deleted_at.is_(None))
    )).all())
    assert len(imported_tasks) == 3
    titles = {t.title for t in imported_tasks}
    assert {"Alpha", "Beta", "Gamma subtask"} == titles


async def test_import_parent_child_preserved(db_session: AsyncSession, stub_user: User):
    p, t1, t2, t3 = await _setup(db_session, stub_user)
    export_data = await project_export_service.export_project(db_session, p.id, stub_user)

    imported = await project_export_service.import_project(
        db_session, export_data, _unique_key(),
        include_comments=True, reset_statuses=False, user=stub_user,
    )

    from sqlalchemy import select
    from app.models.task import Task
    imported_tasks = list((await db_session.scalars(
        select(Task).where(Task.project_id == imported.id, Task.deleted_at.is_(None))
    )).all())
    gamma = next(t for t in imported_tasks if t.title == "Gamma subtask")
    alpha = next(t for t in imported_tasks if t.title == "Alpha")
    assert gamma.parent_task_id == alpha.id


async def test_import_links_preserved(db_session: AsyncSession, stub_user: User):
    p, t1, t2, t3 = await _setup(db_session, stub_user)
    export_data = await project_export_service.export_project(db_session, p.id, stub_user)

    imported = await project_export_service.import_project(
        db_session, export_data, _unique_key(),
        include_comments=True, reset_statuses=False, user=stub_user,
    )

    from sqlalchemy import select
    from app.models.task import Task, TaskLink
    imported_tasks = list((await db_session.scalars(
        select(Task).where(Task.project_id == imported.id, Task.deleted_at.is_(None))
    )).all())
    task_ids = {t.id for t in imported_tasks}

    links = list((await db_session.scalars(
        select(TaskLink).where(
            TaskLink.source_task_id.in_(task_ids),
            TaskLink.target_task_id.in_(task_ids),
        )
    )).all())
    assert len(links) == 1


async def test_import_reset_statuses(db_session: AsyncSession, stub_user: User):
    """With reset_statuses=True all tasks land on the default initial status."""
    p, *_ = await _setup(db_session, stub_user)

    # Advance one task to a non-initial status via update
    from app.models.workflow import Status, StatusCategory, Workflow
    from sqlalchemy import select
    wf = await db_session.scalar(
        select(Workflow).where(Workflow.project_id == p.id, Workflow.is_default.is_(True))
    )
    inprog = await db_session.scalar(
        select(Status).where(
            Status.workflow_id == wf.id,
            Status.category == StatusCategory.intermediate,
        )
    )
    if inprog:
        from app.models.task import Task
        t1_db = await db_session.scalar(
            select(Task).where(Task.project_id == p.id, Task.deleted_at.is_(None)).limit(1)
        )
        t1_db.current_status_id = inprog.id
        await db_session.commit()

    export_data = await project_export_service.export_project(db_session, p.id, stub_user)

    imported = await project_export_service.import_project(
        db_session, export_data, _unique_key(),
        include_comments=False, reset_statuses=True, user=stub_user,
    )

    from app.models.task import Task
    from app.models.workflow import Status, StatusCategory
    imported_tasks = list((await db_session.scalars(
        select(Task).where(Task.project_id == imported.id, Task.deleted_at.is_(None))
    )).all())
    imported_status_ids = {t.current_status_id for t in imported_tasks}
    statuses = list((await db_session.scalars(
        select(Status).where(Status.id.in_(imported_status_ids))
    )).all())
    assert all(s.category == StatusCategory.initial for s in statuses)


async def test_import_exclude_comments(db_session: AsyncSession, stub_user: User):
    """With include_comments=False, no comments are imported."""
    from app.services.comment_service import create_comment
    from app.schemas.comment import CommentCreate
    p, t1, *_ = await _setup(db_session, stub_user)
    await create_comment(db_session, t1.id, CommentCreate(content="note"), stub_user)

    export_data = await project_export_service.export_project(db_session, p.id, stub_user)
    assert any(len(t["comments"]) > 0 for t in export_data["tasks"]), "setup sanity"

    imported = await project_export_service.import_project(
        db_session, export_data, _unique_key(),
        include_comments=False, reset_statuses=False, user=stub_user,
    )

    from app.models.comment import Comment
    from app.models.task import Task
    imported_task_ids = list((await db_session.scalars(
        select(Task.id).where(Task.project_id == imported.id)
    )).all())
    comment_count = await db_session.scalar(
        select(func.count()).select_from(Comment).where(Comment.task_id.in_(imported_task_ids))
    )
    assert comment_count == 0


async def test_import_duplicate_key(db_session: AsyncSession, stub_user: User):
    p, *_ = await _setup(db_session, stub_user)
    export_data = await project_export_service.export_project(db_session, p.id, stub_user)

    # Use the same key as the original project — should conflict
    from fastapi import HTTPException
    with pytest.raises(HTTPException) as exc:
        await project_export_service.import_project(
            db_session, export_data, p.key,
            include_comments=True, reset_statuses=False, user=stub_user,
        )
    assert exc.value.status_code == 409


async def test_import_http(client: AsyncClient, db_session: AsyncSession, stub_user: User):
    p, *_ = await _setup(db_session, stub_user)
    export_data = await project_export_service.export_project(db_session, p.id, stub_user)

    new_key = _unique_key()
    resp = await client.post("/api/v1/projects/import", json={
        "data": export_data,
        "new_key": new_key,
        "include_comments": True,
        "reset_statuses": False,
    })
    assert resp.status_code == 201
    body = resp.json()
    assert body["key"] == new_key
