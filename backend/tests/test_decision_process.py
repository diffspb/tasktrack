"""Decision Process tests — core scenarios S2 & S3."""
import asyncio
import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_session
from app.main import app
from app.models.project import ProjectMember, ProjectMemberRole
from app.models.task import AssigneeRole
from app.models.user import User
from app.models.workflow import StatusCategory
from app.schemas.project import ProjectCreate
from app.schemas.task import AssignmentCreate
from app.schemas.workflow import StatusCreate, TransitionCreate, WorkflowCreate
from app.services import (
    decision_service,
    project_service,
    resolution_service,
    task_service,
    workflow_service,
)
from app.schemas.resolution import ResolutionCreate


def _rnd_key() -> str:
    return uuid.uuid4().hex[:8].upper()


async def _setup(session: AsyncSession, owner: User) -> dict:
    """Project + Basic workflow + Done resolution."""
    project = await project_service.create_project(
        session, ProjectCreate(name="DP test", key=_rnd_key()), owner
    )
    wf = await workflow_service.create_workflow(
        session, project.id, WorkflowCreate(name="Basic"), owner
    )
    todo = await workflow_service.create_status(
        session, wf.id,
        StatusCreate(name="To Do", category=StatusCategory.initial, is_default=True),
        owner,
    )
    inprog = await workflow_service.create_status(
        session, wf.id,
        StatusCreate(name="In Progress", category=StatusCategory.intermediate, position=1),
        owner,
    )
    done = await workflow_service.create_status(
        session, wf.id,
        StatusCreate(name="Done", category=StatusCategory.final, position=2),
        owner,
    )
    await workflow_service.create_transition(
        session, wf.id, TransitionCreate(from_status_id=todo.id, to_status_id=inprog.id), owner
    )
    await workflow_service.create_transition(
        session, wf.id, TransitionCreate(from_status_id=inprog.id, to_status_id=done.id), owner
    )
    resolution = await resolution_service.create_resolution(
        session, project.id, ResolutionCreate(name="Done", is_default=True), owner
    )
    return {
        "project_id": project.id,
        "workflow_id": wf.id,
        "todo_id": todo.id,
        "inprog_id": inprog.id,
        "done_id": done.id,
        "resolution_id": resolution.id,
    }


async def _add_member(session: AsyncSession, project_id, user_id) -> None:
    session.add(ProjectMember(
        project_id=project_id, user_id=user_id, role=ProjectMemberRole.member,
    ))
    await session.flush()


async def _make_user(session: AsyncSession, email: str) -> User:
    u = User(
        id=uuid.uuid4(), email=email, display_name=email.split("@")[0],
        keycloak_id=email, is_active=True,
    )
    session.add(u)
    await session.flush()
    return u


async def _create_task_with_dm(
    session: AsyncSession, ctx: dict, reporter: User, dm: User,
    *, allow_multi_accept: bool = False,
):
    from app.schemas.task import TaskCreate
    return await task_service.create_task(
        session, ctx["project_id"],
        TaskCreate(
            title="DP task", workflow_id=ctx["workflow_id"],
            decision_maker_id=dm.id, allow_multi_accept=allow_multi_accept,
        ),
        reporter,
    )


async def _drive_to_final(session, ctx, assignment_id, user):
    """Move assignment To Do → In Progress → Done(with resolution)."""
    from app.schemas.task import AssignmentTransition
    await task_service.transition_assignment_status(
        session, assignment_id,
        AssignmentTransition(status_id=ctx["inprog_id"]), user,
    )
    await task_service.transition_assignment_status(
        session, assignment_id,
        AssignmentTransition(status_id=ctx["done_id"], resolution_id=ctx["resolution_id"]),
        user,
    )


# ---------------------------------------------------------------------------
# 1. happy path S2
# ---------------------------------------------------------------------------

async def test_s2_happy_path(db_session: AsyncSession, stub_user: User):
    ctx = await _setup(db_session, stub_user)
    other = await _make_user(db_session, "other-s2@test.com")
    await _add_member(db_session, ctx["project_id"], other.id)
    await db_session.commit()

    task = await _create_task_with_dm(db_session, ctx, stub_user, stub_user)

    a1 = await task_service.assign_user(
        db_session, task.id, AssignmentCreate(user_id=stub_user.id, role=AssigneeRole.lead), stub_user
    )
    a2 = await task_service.assign_user(
        db_session, task.id, AssignmentCreate(user_id=other.id, role=AssigneeRole.lead), stub_user
    )

    await _drive_to_final(db_session, ctx, a1.id, stub_user)
    await _drive_to_final(db_session, ctx, a2.id, other)

    from app.schemas.decision import SolutionCreate
    s1 = await decision_service.create_solution(
        db_session, a1.id, SolutionCreate(content="approach 1"), stub_user
    )
    s2 = await decision_service.create_solution(
        db_session, a2.id, SolutionCreate(content="approach 2"), other
    )

    # First submit: only one lead submitted → still in_progress
    sol1, t1 = await decision_service.submit_solution(db_session, s1.id, stub_user)
    assert sol1.status.value == "submitted"
    assert t1 is None  # task didn't transition (other lead still drafting)

    # Second submit: all leads submitted → awaiting_decision
    sol2, t2 = await decision_service.submit_solution(db_session, s2.id, other)
    assert t2 is not None and t2.value == "awaiting_decision"

    from app.schemas.decision import DecisionCreate
    decision = await decision_service.make_decision(
        db_session, task.id,
        DecisionCreate(accepted_solution_ids=[s1.id], note="approach 1 wins"),
        stub_user,
    )
    assert decision.accepted_solution_ids == [s1.id]

    refreshed = await db_session.get(type(task), task.id)
    assert refreshed.global_status.value == "decided"

    # close
    closed = await decision_service.close_task(db_session, task.id, stub_user)
    assert closed.global_status.value == "closed"


# ---------------------------------------------------------------------------
# 2. revision cycle S3
# ---------------------------------------------------------------------------

async def test_s3_revision_cycle(db_session: AsyncSession, stub_user: User):
    ctx = await _setup(db_session, stub_user)
    other = await _make_user(db_session, "other-s3@test.com")
    await _add_member(db_session, ctx["project_id"], other.id)
    await db_session.commit()

    task = await _create_task_with_dm(db_session, ctx, stub_user, stub_user)
    a1 = await task_service.assign_user(
        db_session, task.id, AssignmentCreate(user_id=stub_user.id, role=AssigneeRole.lead), stub_user
    )
    a2 = await task_service.assign_user(
        db_session, task.id, AssignmentCreate(user_id=other.id, role=AssigneeRole.lead), stub_user
    )
    await _drive_to_final(db_session, ctx, a1.id, stub_user)
    await _drive_to_final(db_session, ctx, a2.id, other)

    from app.schemas.decision import SolutionCreate, SolutionUpdate, RevisionRequest
    s1 = await decision_service.create_solution(
        db_session, a1.id, SolutionCreate(content="v1"), stub_user
    )
    s2 = await decision_service.create_solution(
        db_session, a2.id, SolutionCreate(content="approach 2"), other
    )
    await decision_service.submit_solution(db_session, s1.id, stub_user)
    await decision_service.submit_solution(db_session, s2.id, other)

    # DM requests revision on s1
    sol_after, transitioned = await decision_service.request_revision(
        db_session, s1.id, "needs more detail", stub_user
    )
    assert sol_after.status.value == "revision_requested"
    assert transitioned.value == "in_revision"

    # s2 stays submitted, no need to resubmit
    refreshed_s2 = await db_session.get(type(s2), s2.id)
    assert refreshed_s2.status.value == "submitted"

    # author edits and resubmits s1 → back to awaiting_decision
    await decision_service.update_solution(
        db_session, s1.id, SolutionUpdate(content="v2 with details"), stub_user
    )
    sol1_v2, t = await decision_service.submit_solution(db_session, s1.id, stub_user)
    assert sol1_v2.status.value == "submitted"
    assert t.value == "awaiting_decision"

    # Decision wins
    from app.schemas.decision import DecisionCreate
    await decision_service.make_decision(
        db_session, task.id,
        DecisionCreate(accepted_solution_ids=[s1.id]), stub_user,
    )
    refreshed = await db_session.get(type(task), task.id)
    assert refreshed.global_status.value == "decided"


# ---------------------------------------------------------------------------
# 3. concurrent submit
# ---------------------------------------------------------------------------

async def test_concurrent_submit(async_engine, stub_user_seed):
    """Two leads submit simultaneously: both end up submitted, exactly one
    flips global_status to awaiting_decision."""
    from sqlalchemy.ext.asyncio import AsyncSession as AS, async_sessionmaker
    SessionLocal = async_sessionmaker(async_engine, expire_on_commit=False)

    # Setup is committed for real (no savepoint) — concurrent connections
    # need to see the same data.
    async with SessionLocal() as setup_session:
        ctx = await _setup(setup_session, stub_user_seed)
        other = await _make_user(setup_session, "concurrent@test.com")
        await _add_member(setup_session, ctx["project_id"], other.id)
        await setup_session.commit()

        task = await _create_task_with_dm(setup_session, ctx, stub_user_seed, stub_user_seed)
        a1 = await task_service.assign_user(
            setup_session, task.id,
            AssignmentCreate(user_id=stub_user_seed.id, role=AssigneeRole.lead),
            stub_user_seed,
        )
        a2 = await task_service.assign_user(
            setup_session, task.id,
            AssignmentCreate(user_id=other.id, role=AssigneeRole.lead),
            stub_user_seed,
        )
        await _drive_to_final(setup_session, ctx, a1.id, stub_user_seed)
        await _drive_to_final(setup_session, ctx, a2.id, other)

        from app.schemas.decision import SolutionCreate
        s1 = await decision_service.create_solution(
            setup_session, a1.id, SolutionCreate(content="approach 1"), stub_user_seed,
        )
        s2 = await decision_service.create_solution(
            setup_session, a2.id, SolutionCreate(content="approach 2"), other,
        )
        s1_id, s2_id = s1.id, s2.id
        task_id = task.id

    async def submit_in_own_session(sol_id: uuid.UUID, who: User):
        async with SessionLocal() as s:
            return await decision_service.submit_solution(s, sol_id, who)

    results = await asyncio.gather(
        submit_in_own_session(s1_id, stub_user_seed),
        submit_in_own_session(s2_id, other),
    )

    transitions = [t for _, t in results]
    # Exactly one transition value is awaiting_decision; the other is None.
    awaiting = [t for t in transitions if t and t.value == "awaiting_decision"]
    assert len(awaiting) == 1, f"got transitions={transitions}"

    async with SessionLocal() as verify:
        from app.models.task import Task as T
        refreshed = await verify.get(T, task_id)
        assert refreshed.global_status.value == "awaiting_decision"
        # Cleanup so subsequent tests aren't polluted with this committed state.
        await verify.delete(refreshed)
        await verify.commit()


@pytest.fixture
async def stub_user_seed(async_engine):
    """For concurrent test: commit stub user to a real connection so all
    sessions see it."""
    from sqlalchemy.ext.asyncio import async_sessionmaker
    from app.core.auth_stub import STUB_USER_ID
    SessionLocal = async_sessionmaker(async_engine, expire_on_commit=False)
    async with SessionLocal() as s:
        existing = await s.get(User, STUB_USER_ID)
        if existing:
            yield existing
            return
        u = User(
            id=STUB_USER_ID, email="dev@localhost", display_name="Dev User",
            keycloak_id=str(STUB_USER_ID), is_active=True,
        )
        s.add(u)
        await s.commit()
        await s.refresh(u)
        yield u


# ---------------------------------------------------------------------------
# 4. withdraw in revision_requested → 400
# ---------------------------------------------------------------------------

async def test_withdraw_blocked_in_revision(db_session: AsyncSession, stub_user: User):
    ctx = await _setup(db_session, stub_user)
    other = await _make_user(db_session, "wd@test.com")
    await _add_member(db_session, ctx["project_id"], other.id)
    await db_session.commit()

    task = await _create_task_with_dm(db_session, ctx, stub_user, stub_user)
    a1 = await task_service.assign_user(
        db_session, task.id, AssignmentCreate(user_id=stub_user.id, role=AssigneeRole.lead), stub_user,
    )
    a2 = await task_service.assign_user(
        db_session, task.id, AssignmentCreate(user_id=other.id, role=AssigneeRole.lead), stub_user,
    )
    await _drive_to_final(db_session, ctx, a1.id, stub_user)
    await _drive_to_final(db_session, ctx, a2.id, other)

    from app.schemas.decision import SolutionCreate
    s1 = await decision_service.create_solution(db_session, a1.id, SolutionCreate(content="x"), stub_user)
    s2 = await decision_service.create_solution(db_session, a2.id, SolutionCreate(content="y"), other)
    await decision_service.submit_solution(db_session, s1.id, stub_user)
    await decision_service.submit_solution(db_session, s2.id, other)
    await decision_service.request_revision(db_session, s1.id, "redo", stub_user)

    from fastapi import HTTPException
    with pytest.raises(HTTPException) as exc:
        await decision_service.withdraw_solution(db_session, s1.id, stub_user)
    assert exc.value.detail["code"] == "SOLUTION_IN_REVISION"


# ---------------------------------------------------------------------------
# 5. consultant cannot create/submit Solution
# ---------------------------------------------------------------------------

async def test_consultant_cannot_create_solution(db_session: AsyncSession, stub_user: User):
    ctx = await _setup(db_session, stub_user)

    task = await _create_task_with_dm(db_session, ctx, stub_user, stub_user)
    a = await task_service.assign_user(
        db_session, task.id,
        AssignmentCreate(user_id=stub_user.id, role=AssigneeRole.consultant),
        stub_user,
    )

    from app.schemas.decision import SolutionCreate
    from fastapi import HTTPException
    with pytest.raises(HTTPException) as exc:
        await decision_service.create_solution(
            db_session, a.id, SolutionCreate(content="x"), stub_user
        )
    assert exc.value.status_code == 403


# ---------------------------------------------------------------------------
# 6. consultant doesn't see others' solutions until Decision
# ---------------------------------------------------------------------------

async def test_consultant_cannot_see_others_solutions_before_decision(
    db_session: AsyncSession, stub_user: User
):
    """Multi-lead DP: consultant is denied access to others' solutions
    until TaskDecision is made."""
    ctx = await _setup(db_session, stub_user)
    leader = await _make_user(db_session, "leader@test.com")
    leader2 = await _make_user(db_session, "leader2@test.com")
    await _add_member(db_session, ctx["project_id"], leader.id)
    await _add_member(db_session, ctx["project_id"], leader2.id)
    await db_session.commit()

    # DM is leader (not stub_user — stub is the consultant).
    task = await _create_task_with_dm(db_session, ctx, stub_user, leader)
    a_lead = await task_service.assign_user(
        db_session, task.id,
        AssignmentCreate(user_id=leader.id, role=AssigneeRole.lead), stub_user,
    )
    a_lead2 = await task_service.assign_user(
        db_session, task.id,
        AssignmentCreate(user_id=leader2.id, role=AssigneeRole.lead), stub_user,
    )
    await task_service.assign_user(
        db_session, task.id,
        AssignmentCreate(user_id=stub_user.id, role=AssigneeRole.consultant), stub_user,
    )
    await _drive_to_final(db_session, ctx, a_lead.id, leader)
    await _drive_to_final(db_session, ctx, a_lead2.id, leader2)

    from app.schemas.decision import SolutionCreate
    s = await decision_service.create_solution(
        db_session, a_lead.id, SolutionCreate(content="approach"), leader
    )
    await decision_service.submit_solution(db_session, s.id, leader)

    from fastapi import HTTPException
    with pytest.raises(HTTPException) as exc:
        await decision_service.list_task_solutions(db_session, task.id, stub_user)
    assert exc.value.status_code == 403

    with pytest.raises(HTTPException) as exc:
        await decision_service.get_solution_by_assignment(db_session, a_lead.id, stub_user)
    assert exc.value.status_code == 403


# ---------------------------------------------------------------------------
# 7. DecisionCriteria locked after first submit
# ---------------------------------------------------------------------------

async def test_criteria_locked_after_submit(db_session: AsyncSession, stub_user: User):
    ctx = await _setup(db_session, stub_user)
    other = await _make_user(db_session, "crit@test.com")
    await _add_member(db_session, ctx["project_id"], other.id)
    await db_session.commit()

    task = await _create_task_with_dm(db_session, ctx, stub_user, stub_user)
    from app.schemas.decision import DecisionCriteriaItem, DecisionCriteriaReplace
    await decision_service.replace_criteria(
        db_session, task.id,
        DecisionCriteriaReplace(items=[DecisionCriteriaItem(description="speed", position=0)]),
        stub_user,
    )

    a = await task_service.assign_user(
        db_session, task.id,
        AssignmentCreate(user_id=stub_user.id, role=AssigneeRole.lead),
        stub_user,
    )
    a2 = await task_service.assign_user(
        db_session, task.id,
        AssignmentCreate(user_id=other.id, role=AssigneeRole.lead),
        stub_user,
    )
    await _drive_to_final(db_session, ctx, a.id, stub_user)
    await _drive_to_final(db_session, ctx, a2.id, other)

    from app.schemas.decision import SolutionCreate
    s = await decision_service.create_solution(
        db_session, a.id, SolutionCreate(content="x"), stub_user
    )
    await decision_service.submit_solution(db_session, s.id, stub_user)

    # criteria is now locked
    items = await decision_service.list_criteria(db_session, task.id, stub_user)
    assert all(c.is_locked for c in items)

    from fastapi import HTTPException
    with pytest.raises(HTTPException) as exc:
        await decision_service.replace_criteria(
            db_session, task.id,
            DecisionCriteriaReplace(items=[DecisionCriteriaItem(description="cost", position=0)]),
            stub_user,
        )
    assert exc.value.detail["code"] == "CRITERIA_LOCKED"


# ---------------------------------------------------------------------------
# 8. multi-accept disabled → multiple ids → 400
# ---------------------------------------------------------------------------

async def test_multi_accept_disabled(db_session: AsyncSession, stub_user: User):
    ctx = await _setup(db_session, stub_user)
    other = await _make_user(db_session, "ma-other@test.com")
    await _add_member(db_session, ctx["project_id"], other.id)
    await db_session.commit()

    task = await _create_task_with_dm(
        db_session, ctx, stub_user, stub_user, allow_multi_accept=False
    )
    a1 = await task_service.assign_user(
        db_session, task.id, AssignmentCreate(user_id=stub_user.id, role=AssigneeRole.lead), stub_user,
    )
    a2 = await task_service.assign_user(
        db_session, task.id, AssignmentCreate(user_id=other.id, role=AssigneeRole.lead), stub_user,
    )
    await _drive_to_final(db_session, ctx, a1.id, stub_user)
    await _drive_to_final(db_session, ctx, a2.id, other)

    from app.schemas.decision import SolutionCreate, DecisionCreate
    s1 = await decision_service.create_solution(db_session, a1.id, SolutionCreate(content="x"), stub_user)
    s2 = await decision_service.create_solution(db_session, a2.id, SolutionCreate(content="y"), other)
    await decision_service.submit_solution(db_session, s1.id, stub_user)
    await decision_service.submit_solution(db_session, s2.id, other)

    from fastapi import HTTPException
    with pytest.raises(HTTPException) as exc:
        await decision_service.make_decision(
            db_session, task.id,
            DecisionCreate(accepted_solution_ids=[s1.id, s2.id]),
            stub_user,
        )
    assert exc.value.detail["code"] == "MULTI_ACCEPT_NOT_ALLOWED"


async def test_multi_accept_enabled(db_session: AsyncSession, stub_user: User):
    ctx = await _setup(db_session, stub_user)
    other = await _make_user(db_session, "ma-en@test.com")
    await _add_member(db_session, ctx["project_id"], other.id)
    await db_session.commit()

    task = await _create_task_with_dm(
        db_session, ctx, stub_user, stub_user, allow_multi_accept=True
    )
    a1 = await task_service.assign_user(
        db_session, task.id, AssignmentCreate(user_id=stub_user.id, role=AssigneeRole.lead), stub_user,
    )
    a2 = await task_service.assign_user(
        db_session, task.id, AssignmentCreate(user_id=other.id, role=AssigneeRole.lead), stub_user,
    )
    await _drive_to_final(db_session, ctx, a1.id, stub_user)
    await _drive_to_final(db_session, ctx, a2.id, other)

    from app.schemas.decision import SolutionCreate, DecisionCreate
    s1 = await decision_service.create_solution(db_session, a1.id, SolutionCreate(content="x"), stub_user)
    s2 = await decision_service.create_solution(db_session, a2.id, SolutionCreate(content="y"), other)
    await decision_service.submit_solution(db_session, s1.id, stub_user)
    await decision_service.submit_solution(db_session, s2.id, other)

    decision = await decision_service.make_decision(
        db_session, task.id,
        DecisionCreate(accepted_solution_ids=[s1.id, s2.id]),
        stub_user,
    )
    assert set(decision.accepted_solution_ids) == {s1.id, s2.id}


# ---------------------------------------------------------------------------
# 9. submit twice → SOLUTION_ALREADY_SUBMITTED
# ---------------------------------------------------------------------------

async def test_submit_twice_blocked(db_session: AsyncSession, stub_user: User):
    ctx = await _setup(db_session, stub_user)
    other = await _make_user(db_session, "twice@test.com")
    await _add_member(db_session, ctx["project_id"], other.id)
    await db_session.commit()

    task = await _create_task_with_dm(db_session, ctx, stub_user, stub_user)
    a = await task_service.assign_user(
        db_session, task.id, AssignmentCreate(user_id=stub_user.id, role=AssigneeRole.lead), stub_user,
    )
    a2 = await task_service.assign_user(
        db_session, task.id, AssignmentCreate(user_id=other.id, role=AssigneeRole.lead), stub_user,
    )
    await _drive_to_final(db_session, ctx, a.id, stub_user)
    await _drive_to_final(db_session, ctx, a2.id, other)

    from app.schemas.decision import SolutionCreate
    s = await decision_service.create_solution(db_session, a.id, SolutionCreate(content="x"), stub_user)
    await decision_service.submit_solution(db_session, s.id, stub_user)

    from fastapi import HTTPException
    with pytest.raises(HTTPException) as exc:
        await decision_service.submit_solution(db_session, s.id, stub_user)
    assert exc.value.detail["code"] == "SOLUTION_ALREADY_SUBMITTED"


# ---------------------------------------------------------------------------
# 10. make_decision before awaiting_decision → 400
# ---------------------------------------------------------------------------

async def test_make_decision_before_awaiting(db_session: AsyncSession, stub_user: User):
    ctx = await _setup(db_session, stub_user)
    task = await _create_task_with_dm(db_session, ctx, stub_user, stub_user)
    a = await task_service.assign_user(
        db_session, task.id, AssignmentCreate(user_id=stub_user.id, role=AssigneeRole.lead), stub_user,
    )

    from app.schemas.decision import DecisionCreate
    from fastapi import HTTPException
    with pytest.raises(HTTPException) as exc:
        await decision_service.make_decision(
            db_session, task.id,
            DecisionCreate(accepted_solution_ids=[uuid.uuid4()]),
            stub_user,
        )
    assert exc.value.detail["code"] == "TASK_NOT_AWAITING_DECISION"


# ---------------------------------------------------------------------------
# 11. HTTP integration: full S2 over the API
# ---------------------------------------------------------------------------

async def test_s2_via_http(client: AsyncClient, db_session: AsyncSession, stub_user: User):
    ctx = await _setup(db_session, stub_user)
    other = await _make_user(db_session, "http-s2@test.com")
    await _add_member(db_session, ctx["project_id"], other.id)
    await db_session.commit()

    r = await client.post(f"/api/v1/projects/{ctx['project_id']}/tasks", json={
        "title": "HTTP DP", "workflow_id": str(ctx["workflow_id"]),
        "decision_maker_id": str(stub_user.id),
    })
    task_id = r.json()["id"]

    a1 = (await client.post(f"/api/v1/tasks/{task_id}/assignments", json={
        "user_id": str(stub_user.id), "role": "lead",
    })).json()

    # Add other as lead via service (HTTP only knows stub_user)
    a2 = await task_service.assign_user(
        db_session, uuid.UUID(task_id),
        AssignmentCreate(user_id=other.id, role=AssigneeRole.lead),
        stub_user,
    )

    # Drive both to final
    for aid, who in ((a1["id"], stub_user), (str(a2.id), other)):
        if who is stub_user:
            for status_id in (str(ctx["inprog_id"]), str(ctx["done_id"])):
                body = {"status_id": status_id}
                if status_id == str(ctx["done_id"]):
                    body["resolution_id"] = str(ctx["resolution_id"])
                await client.patch(f"/api/v1/assignments/{aid}/status", json=body)
        else:
            await _drive_to_final(db_session, ctx, uuid.UUID(aid), who)

    # Create + submit Solution for a1 via HTTP
    s1 = await client.post(f"/api/v1/assignments/{a1['id']}/solution", json={"content": "x"})
    assert s1.status_code == 201
    submit_r = await client.post(f"/api/v1/solutions/{s1.json()['id']}/submit")
    assert submit_r.status_code == 200
    assert submit_r.json()["task_transitioned_to"] is None

    # Solution for a2 via service (HTTP would auth as stub_user)
    from app.schemas.decision import SolutionCreate
    s2 = await decision_service.create_solution(
        db_session, a2.id, SolutionCreate(content="y"), other
    )
    _, t = await decision_service.submit_solution(db_session, s2.id, other)
    assert t.value == "awaiting_decision"

    # DM (stub_user) makes decision via HTTP
    dec_r = await client.post(f"/api/v1/tasks/{task_id}/decisions", json={
        "accepted_solution_ids": [s1.json()["id"]],
        "note": "wins",
    })
    assert dec_r.status_code == 201
    assert (await client.get(f"/api/v1/tasks/{task_id}")).json()["global_status"] == "decided"

    close_r = await client.post(f"/api/v1/tasks/{task_id}/close")
    assert close_r.status_code == 200
    assert close_r.json()["global_status"] == "closed"
