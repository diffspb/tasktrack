"""FTS-поиск через PostgreSQL tsvector с конфигурацией russian."""
import uuid

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.models.workflow import StatusCategory
from app.schemas.project import ProjectCreate
from app.schemas.task import TaskCreate
from app.schemas.workflow import StatusCreate, WorkflowCreate
from app.services import project_service, task_service, workflow_service


def _rnd_key() -> str:
    return uuid.uuid4().hex[:8].upper()


async def _setup(db_session: AsyncSession, user: User) -> dict:
    project = await project_service.create_project(
        db_session, ProjectCreate(name="Search test", key=_rnd_key()), user
    )
    wf = await workflow_service.create_workflow(
        db_session, project.id, WorkflowCreate(name="Basic"), user
    )
    await workflow_service.create_status(
        db_session, wf.id,
        StatusCreate(name="To Do", category=StatusCategory.initial, is_default=True),
        user,
    )
    return {"project_id": project.id, "workflow_id": wf.id}


async def test_search_finds_by_title(
    client: AsyncClient, db_session: AsyncSession, stub_user: User
):
    ctx = await _setup(db_session, stub_user)
    await task_service.create_task(
        db_session, ctx["project_id"],
        TaskCreate(title="Реализовать авторизацию через Keycloak",
                   workflow_id=ctx["workflow_id"]),
        stub_user,
    )
    await task_service.create_task(
        db_session, ctx["project_id"],
        TaskCreate(title="Настроить CI/CD pipeline",
                   workflow_id=ctx["workflow_id"]),
        stub_user,
    )

    r = await client.get("/api/v1/search?q=авторизация")
    assert r.status_code == 200
    items = r.json()["items"]
    assert len(items) == 1
    assert "авторизац" in items[0]["title"].lower()


async def test_search_uses_russian_stemmer(
    client: AsyncClient, db_session: AsyncSession, stub_user: User
):
    """Поиск по 'авторизация' должен находить 'авторизации' (разные формы)."""
    ctx = await _setup(db_session, stub_user)
    await task_service.create_task(
        db_session, ctx["project_id"],
        TaskCreate(
            title="Доделать модуль",
            description="Уделить внимание авторизации пользователей",
            workflow_id=ctx["workflow_id"],
        ),
        stub_user,
    )
    r = await client.get("/api/v1/search?q=авторизация")
    items = r.json()["items"]
    assert len(items) == 1


async def test_search_filters_by_project(
    client: AsyncClient, db_session: AsyncSession, stub_user: User
):
    ctx_a = await _setup(db_session, stub_user)
    ctx_b = await _setup(db_session, stub_user)

    await task_service.create_task(
        db_session, ctx_a["project_id"],
        TaskCreate(title="Авторизация в проекте А", workflow_id=ctx_a["workflow_id"]),
        stub_user,
    )
    await task_service.create_task(
        db_session, ctx_b["project_id"],
        TaskCreate(title="Авторизация в проекте Б", workflow_id=ctx_b["workflow_id"]),
        stub_user,
    )

    all_r = (await client.get("/api/v1/search?q=авторизация")).json()
    assert len(all_r["items"]) == 2

    only_a = (await client.get(
        f"/api/v1/search?q=авторизация&project_id={ctx_a['project_id']}"
    )).json()
    assert len(only_a["items"]) == 1
    assert "проекте А" in only_a["items"][0]["title"]


async def test_search_skips_soft_deleted(
    client: AsyncClient, db_session: AsyncSession, stub_user: User
):
    ctx = await _setup(db_session, stub_user)
    t = await task_service.create_task(
        db_session, ctx["project_id"],
        TaskCreate(title="Скоро удалим", workflow_id=ctx["workflow_id"]),
        stub_user,
    )
    await task_service.delete_task(db_session, t.id, stub_user)

    r = await client.get("/api/v1/search?q=удалим")
    assert r.json()["items"] == []


async def test_search_empty_query_returns_nothing(
    client: AsyncClient, db_session: AsyncSession, stub_user: User
):
    ctx = await _setup(db_session, stub_user)
    await task_service.create_task(
        db_session, ctx["project_id"],
        TaskCreate(title="Anything", workflow_id=ctx["workflow_id"]),
        stub_user,
    )
    r = await client.get("/api/v1/search?q=")
    assert r.json()["items"] == []
