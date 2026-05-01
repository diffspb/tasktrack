"""Notifications: emit on Decision Process events + read API."""
import uuid

from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notification import Notification, NotificationEventType
from app.models.task import AssigneeRole
from app.models.project import ProjectMember, ProjectMemberRole
from app.models.user import User
from app.models.workflow import StatusCategory
from app.schemas.decision import DecisionCreate, SolutionCreate
from app.schemas.project import ProjectCreate
from app.schemas.resolution import ResolutionCreate
from app.schemas.task import AssignmentCreate, AssignmentTransition, TaskCreate
from app.schemas.workflow import StatusCreate, TransitionCreate, WorkflowCreate
from app.services import (
    decision_service,
    project_service,
    resolution_service,
    task_service,
    workflow_service,
)


def _rnd_key() -> str:
    return uuid.uuid4().hex[:8].upper()


async def _setup(session: AsyncSession, owner: User) -> dict:
    project = await project_service.create_project(
        session, ProjectCreate(name="N test", key=_rnd_key()), owner
    )
    wf = await workflow_service.create_workflow(
        session, project.id, WorkflowCreate(name="Basic"), owner
    )
    todo = await workflow_service.create_status(
        session, wf.id, StatusCreate(name="To Do", category=StatusCategory.initial, is_default=True), owner,
    )
    inprog = await workflow_service.create_status(
        session, wf.id, StatusCreate(name="In Progress", category=StatusCategory.intermediate, position=1), owner,
    )
    done = await workflow_service.create_status(
        session, wf.id, StatusCreate(name="Done", category=StatusCategory.final, position=2), owner,
    )
    await workflow_service.create_transition(
        session, wf.id, TransitionCreate(from_status_id=todo.id, to_status_id=inprog.id), owner,
    )
    await workflow_service.create_transition(
        session, wf.id, TransitionCreate(from_status_id=inprog.id, to_status_id=done.id), owner,
    )
    resolution = await resolution_service.create_resolution(
        session, project.id, ResolutionCreate(name="Done", is_default=True), owner,
    )
    return {
        "project_id": project.id, "workflow_id": wf.id,
        "todo_id": todo.id, "inprog_id": inprog.id,
        "done_id": done.id, "resolution_id": resolution.id,
    }


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


async def _drive_to_final(session, ctx, assignment_id, user):
    await task_service.transition_assignment_status(
        session, assignment_id,
        AssignmentTransition(status_id=ctx["inprog_id"]), user,
    )
    await task_service.transition_assignment_status(
        session, assignment_id,
        AssignmentTransition(status_id=ctx["done_id"], resolution_id=ctx["resolution_id"]),
        user,
    )


async def test_assign_creates_notification_for_target(
    db_session: AsyncSession, stub_user: User
):
    ctx = await _setup(db_session, stub_user)
    other = await _make_user(db_session, "n-assign@test.com")
    await _add_member(db_session, ctx["project_id"], other.id)
    await db_session.commit()

    task = await task_service.create_task(
        db_session, ctx["project_id"],
        TaskCreate(title="t", workflow_id=ctx["workflow_id"]), stub_user,
    )
    await task_service.assign_user(
        db_session, task.id,
        AssignmentCreate(user_id=other.id, role=AssigneeRole.lead), stub_user,
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
    task = await task_service.create_task(
        db_session, ctx["project_id"],
        TaskCreate(title="t", workflow_id=ctx["workflow_id"]), stub_user,
    )
    await task_service.assign_user(
        db_session, task.id,
        AssignmentCreate(user_id=stub_user.id, role=AssigneeRole.lead), stub_user,
    )
    rows = (await db_session.scalars(
        select(Notification).where(Notification.recipient_id == stub_user.id)
    )).all()
    assert rows == []


async def test_awaiting_decision_notifies_dm(db_session: AsyncSession, stub_user: User):
    ctx = await _setup(db_session, stub_user)
    other = await _make_user(db_session, "n-dm@test.com")
    dm = await _make_user(db_session, "n-dm-target@test.com")
    await _add_member(db_session, ctx["project_id"], other.id)
    await _add_member(db_session, ctx["project_id"], dm.id)
    await db_session.commit()

    task = await task_service.create_task(
        db_session, ctx["project_id"],
        TaskCreate(title="t", workflow_id=ctx["workflow_id"], decision_maker_id=dm.id),
        stub_user,
    )
    a1 = await task_service.assign_user(
        db_session, task.id,
        AssignmentCreate(user_id=stub_user.id, role=AssigneeRole.lead), stub_user,
    )
    a2 = await task_service.assign_user(
        db_session, task.id,
        AssignmentCreate(user_id=other.id, role=AssigneeRole.lead), stub_user,
    )
    await _drive_to_final(db_session, ctx, a1.id, stub_user)
    await _drive_to_final(db_session, ctx, a2.id, other)

    s1 = await decision_service.create_solution(db_session, a1.id, SolutionCreate(content="x"), stub_user)
    s2 = await decision_service.create_solution(db_session, a2.id, SolutionCreate(content="y"), other)
    await decision_service.submit_solution(db_session, s1.id, stub_user)
    await decision_service.submit_solution(db_session, s2.id, other)

    dm_notifs = (await db_session.scalars(
        select(Notification).where(
            Notification.recipient_id == dm.id,
            Notification.event_type == NotificationEventType.awaiting_decision,
        )
    )).all()
    assert len(dm_notifs) == 1


async def test_revision_notifies_target_lead(db_session: AsyncSession, stub_user: User):
    ctx = await _setup(db_session, stub_user)
    other = await _make_user(db_session, "n-rev@test.com")
    await _add_member(db_session, ctx["project_id"], other.id)
    await db_session.commit()

    task = await task_service.create_task(
        db_session, ctx["project_id"],
        TaskCreate(title="t", workflow_id=ctx["workflow_id"], decision_maker_id=stub_user.id),
        stub_user,
    )
    a1 = await task_service.assign_user(
        db_session, task.id,
        AssignmentCreate(user_id=stub_user.id, role=AssigneeRole.lead), stub_user,
    )
    a2 = await task_service.assign_user(
        db_session, task.id,
        AssignmentCreate(user_id=other.id, role=AssigneeRole.lead), stub_user,
    )
    await _drive_to_final(db_session, ctx, a1.id, stub_user)
    await _drive_to_final(db_session, ctx, a2.id, other)

    s2 = await decision_service.create_solution(db_session, a2.id, SolutionCreate(content="other approach"), other)
    await decision_service.submit_solution(db_session, s2.id, other)
    s1 = await decision_service.create_solution(db_session, a1.id, SolutionCreate(content="my approach"), stub_user)
    await decision_service.submit_solution(db_session, s1.id, stub_user)

    await decision_service.request_revision(db_session, s2.id, "needs more detail", stub_user)

    notifs = (await db_session.scalars(
        select(Notification).where(
            Notification.recipient_id == other.id,
            Notification.event_type == NotificationEventType.revision_requested,
        )
    )).all()
    assert len(notifs) == 1
    assert "needs more detail" in notifs[0].message


async def test_decision_notifies_all_leads(db_session: AsyncSession, stub_user: User):
    ctx = await _setup(db_session, stub_user)
    other = await _make_user(db_session, "n-dec@test.com")
    await _add_member(db_session, ctx["project_id"], other.id)
    await db_session.commit()

    task = await task_service.create_task(
        db_session, ctx["project_id"],
        TaskCreate(title="t", workflow_id=ctx["workflow_id"], decision_maker_id=stub_user.id),
        stub_user,
    )
    a1 = await task_service.assign_user(
        db_session, task.id,
        AssignmentCreate(user_id=stub_user.id, role=AssigneeRole.lead), stub_user,
    )
    a2 = await task_service.assign_user(
        db_session, task.id,
        AssignmentCreate(user_id=other.id, role=AssigneeRole.lead), stub_user,
    )
    await _drive_to_final(db_session, ctx, a1.id, stub_user)
    await _drive_to_final(db_session, ctx, a2.id, other)

    s1 = await decision_service.create_solution(db_session, a1.id, SolutionCreate(content="x"), stub_user)
    s2 = await decision_service.create_solution(db_session, a2.id, SolutionCreate(content="y"), other)
    await decision_service.submit_solution(db_session, s1.id, stub_user)
    await decision_service.submit_solution(db_session, s2.id, other)

    await decision_service.make_decision(
        db_session, task.id,
        DecisionCreate(accepted_solution_ids=[s1.id]), stub_user,
    )

    for uid in (stub_user.id, other.id):
        rows = (await db_session.scalars(
            select(Notification).where(
                Notification.recipient_id == uid,
                Notification.event_type == NotificationEventType.decision_made,
            )
        )).all()
        assert len(rows) == 1


async def test_list_and_mark_read(client: AsyncClient, db_session: AsyncSession, stub_user: User):
    ctx = await _setup(db_session, stub_user)
    task = await task_service.create_task(
        db_session, ctx["project_id"],
        TaskCreate(title="t", workflow_id=ctx["workflow_id"]), stub_user,
    )

    from app.services.notification_service import notify
    from app.models.notification import NotificationEntityType
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
