"""Notifications: emit on task events + read API."""
import uuid

from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notification import Notification, NotificationEntityType, NotificationEventType
from app.models.project import ProjectMember, ProjectMemberRole
from app.models.user import User
from app.schemas.project import ProjectCreate
from app.schemas.task import TaskCreate, TaskUpdate
from app.services import project_service, task_service


def _rnd_key() -> str:
    return uuid.uuid4().hex[:8].upper()


async def _setup(session: AsyncSession, owner: User) -> dict:
    project = await project_service.create_project(
        session, ProjectCreate(name="N test", key=_rnd_key()), owner
    )
    return {"project_id": project.id}


async def _make_user(session: AsyncSession, email: str) -> User:
    u = User(
        id=uuid.uuid4(), email=email, display_name=email.split("@")[0],
        keycloak_id=email, is_active=True,
    )
    session.add(u)
    await session.flush()
    return u


async def _add_member(session: AsyncSession, project_id, user_id) -> None:
    session.add(ProjectMember(
        project_id=project_id, user_id=user_id, role=ProjectMemberRole.member,
    ))
    await session.flush()


async def test_create_task_with_assignee_notifies(
    db_session: AsyncSession, stub_user: User
):
    ctx = await _setup(db_session, stub_user)
    other = await _make_user(db_session, "n-assign@test.com")
    await _add_member(db_session, ctx["project_id"], other.id)
    await db_session.commit()

    await task_service.create_task(
        db_session, ctx["project_id"],
        TaskCreate(title="t", assignee_id=other.id),
        stub_user,
    )

    rows = (await db_session.scalars(
        select(Notification).where(Notification.recipient_id == other.id)
    )).all()
    assert len(rows) == 1
    assert rows[0].event_type == NotificationEventType.task_assigned


async def test_self_assign_does_not_notify(
    db_session: AsyncSession, stub_user: User
):
    ctx = await _setup(db_session, stub_user)
    await db_session.commit()

    await task_service.create_task(
        db_session, ctx["project_id"],
        TaskCreate(title="t", assignee_id=stub_user.id),
        stub_user,
    )
    rows = (await db_session.scalars(
        select(Notification).where(Notification.recipient_id == stub_user.id)
    )).all()
    assert rows == []


async def test_update_assignee_notifies_new_assignee(
    db_session: AsyncSession, stub_user: User
):
    ctx = await _setup(db_session, stub_user)
    other = await _make_user(db_session, "n-update@test.com")
    await _add_member(db_session, ctx["project_id"], other.id)
    await db_session.commit()

    task = await task_service.create_task(
        db_session, ctx["project_id"],
        TaskCreate(title="t"),
        stub_user,
    )
    await task_service.update_task(
        db_session, task.id,
        TaskUpdate(assignee_id=other.id, version=task.version),
        stub_user,
    )

    rows = (await db_session.scalars(
        select(Notification).where(
            Notification.recipient_id == other.id,
            Notification.event_type == NotificationEventType.task_assigned,
        )
    )).all()
    assert len(rows) == 1


async def test_list_and_mark_read(
    client: AsyncClient, db_session: AsyncSession, stub_user: User
):
    ctx = await _setup(db_session, stub_user)
    task = await task_service.create_task(
        db_session, ctx["project_id"],
        TaskCreate(title="t"),
        stub_user,
    )

    from app.services.notification_service import notify
    for i in range(3):
        await notify(
            db_session,
            recipient_id=stub_user.id,
            event_type=NotificationEventType.task_assigned,
            entity_type=NotificationEntityType.task,
            entity_id=task.id,
            task_id=task.id,
            message=f"n{i}",
        )
    await db_session.commit()

    r = await client.get("/api/v1/notifications")
    assert r.status_code == 200
    body = r.json()
    assert body["total"] == 3
    assert body["unread_count"] == 3
    assert len(body["items"]) == 3

    one_id = body["items"][0]["id"]
    pr = await client.patch(f"/api/v1/notifications/{one_id}", json={"is_read": True})
    assert pr.status_code == 200
    assert pr.json()["is_read"] is True

    body2 = (await client.get("/api/v1/notifications")).json()
    assert body2["unread_count"] == 2

    only_unread = (await client.get("/api/v1/notifications?is_read=false")).json()
    assert only_unread["total"] == 2

    rr = await client.post("/api/v1/notifications/read-all")
    assert rr.status_code == 204
    body3 = (await client.get("/api/v1/notifications")).json()
    assert body3["unread_count"] == 0
