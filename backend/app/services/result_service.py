"""Result proposals and independent review (ADR-016, ADR-021, FR-003 TT-14–17).

Rules:
- the task's assignee submits a proposal; its content never changes, a
  correction is a new version (supersedes the previous one);
- a review needs the reviewer profile in the project; the proposal's author
  and the task's assignee never review; a designated reviewer, if set, is the
  only one who may;
- "accepted" requires a rationale and every required criterion marked met;
- Task.result_state is recomputed from the proposals after every change.
"""
import uuid
from datetime import UTC, datetime

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.notification import NotificationEntityType, NotificationEventType
from app.models.project import ProjectMember, ProjectMemberRole
from app.models.result import ProposalStatus, ResultProposal, Review, ReviewVerdict
from app.models.task import Task
from app.models.user import User
from app.models.work_package import WorkPackage
from app.schemas.result import (
    DeliveryCreate, MemberUpdate, ProposalCreate, RecipientAcceptanceCreate, ReviewCreate,
)
from app.services import audit_service, notification_service
from app.services.permissions import get_member, has_role, require_manager, require_writer
from app.services.task_service import get_task

# Proposals that still speak for the task (withdrawn / superseded ones do not).
_LIVE = (
    ProposalStatus.submitted, ProposalStatus.accepted, ProposalStatus.changes_requested,
    ProposalStatus.rejected, ProposalStatus.historical,
)
_VERDICT_STATUS = {
    ReviewVerdict.accepted: ProposalStatus.accepted,
    ReviewVerdict.changes_requested: ProposalStatus.changes_requested,
    ReviewVerdict.rejected: ProposalStatus.rejected,
}
# Verdicts after which work on the task is finished (accepted result or reasoned refusal).
REVIEWED_STATES = frozenset({"accepted", "rejected"})


# ── Proposals ────────────────────────────────────────────────────────────────

async def submit_proposal(
    session: AsyncSession, task_id: uuid.UUID, data: ProposalCreate, user: User
) -> ResultProposal:
    task = await get_task(session, task_id, user, for_update=True)
    await require_writer(session, task.project_id, user)
    if task.assignee_id != user.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, {"code": "NOT_ASSIGNEE"})

    package = await _resolve_package(session, task, data.work_package_id)
    known = _criteria_keys(package)
    unknown = [c.key for c in data.criteria if known is not None and c.key not in known]
    if unknown:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT,
                            {"code": "UNKNOWN_CRITERION", "criteria": unknown})

    previous = None
    if data.supersedes_id:
        previous = await session.scalar(
            select(ResultProposal).where(ResultProposal.id == data.supersedes_id).with_for_update()
        )
        if previous is None or previous.task_id != task.id:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, {"code": "PROPOSAL_NOT_FOUND"})
        if previous.status not in (ProposalStatus.submitted, ProposalStatus.changes_requested):
            raise HTTPException(status.HTTP_409_CONFLICT, {"code": "PROPOSAL_NOT_SUPERSEDABLE"})

    version = (await session.scalar(
        select(func.max(ResultProposal.version)).where(ResultProposal.task_id == task.id)
    ) or 0) + 1
    proposal = ResultProposal(
        task_id=task.id, version=version, author_id=user.id,
        work_package_id=package.id if package else None,
        supersedes_id=previous.id if previous else None,
        status=ProposalStatus.submitted,
        summary=data.summary,
        links=[link.model_dump() for link in data.links],
        criteria=[c.model_dump() for c in data.criteria],
        checks=[c.model_dump() for c in data.checks],
        limitations=data.limitations,
        provenance=data.provenance,
    )
    session.add(proposal)
    await session.flush()
    if previous is not None:
        previous.status = ProposalStatus.superseded
    await _audit(session, task, user, "result_proposal", proposal.id, "created", after={
        "version": version, "work_package_id": str(proposal.work_package_id) if package else None,
        "supersedes_id": str(previous.id) if previous else None,
    })
    await _recompute_state(session, task)
    if task.reviewer_id:
        await notification_service.notify(
            session, recipient_id=task.reviewer_id,
            event_type=NotificationEventType.review_requested,
            entity_type=NotificationEntityType.result_proposal, entity_id=proposal.id,
            task_id=task.id, message=f"Ждёт проверки: {task.key} — {task.title} (версия {version})",
        )
    await session.commit()
    return await get_proposal(session, proposal.id, user)


async def withdraw_proposal(session: AsyncSession, proposal_id: uuid.UUID, user: User) -> ResultProposal:
    proposal, task = await _load_for_update(session, proposal_id, user)
    if proposal.author_id != user.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, {"code": "PERMISSION_DENIED"})
    if proposal.status != ProposalStatus.submitted:
        raise HTTPException(status.HTTP_409_CONFLICT, {"code": "PROPOSAL_NOT_WITHDRAWABLE"})
    proposal.status = ProposalStatus.withdrawn
    await _audit(session, task, user, "result_proposal", proposal.id, "withdrawn",
                 before={"status": "submitted"}, after={"status": "withdrawn"})
    await _recompute_state(session, task)
    await session.commit()
    return await get_proposal(session, proposal.id, user)


async def list_proposals(session: AsyncSession, task_id: uuid.UUID, user: User) -> list[ResultProposal]:
    await get_task(session, task_id, user)
    return list((await session.scalars(
        select(ResultProposal).options(selectinload(ResultProposal.reviews))
        .where(ResultProposal.task_id == task_id).order_by(ResultProposal.version)
    )).all())


async def get_proposal(session: AsyncSession, proposal_id: uuid.UUID, user: User) -> ResultProposal:
    proposal = await session.scalar(
        select(ResultProposal).options(selectinload(ResultProposal.reviews))
        .where(ResultProposal.id == proposal_id)
        .execution_options(populate_existing=True)
    )
    if proposal is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, {"code": "PROPOSAL_NOT_FOUND"})
    await get_task(session, proposal.task_id, user)  # read access
    return proposal


# ── Review ───────────────────────────────────────────────────────────────────

async def review_proposal(
    session: AsyncSession, proposal_id: uuid.UUID, data: ReviewCreate, user: User
) -> Review:
    proposal, task = await _load_for_update(session, proposal_id, user)
    await _require_reviewer(session, task, proposal, user)
    if proposal.status != ProposalStatus.submitted:
        raise HTTPException(status.HTTP_409_CONFLICT, {"code": "PROPOSAL_NOT_REVIEWABLE"})

    package = await session.get(WorkPackage, proposal.work_package_id) if proposal.work_package_id else None
    known = _criteria_keys(package) or {c["key"] for c in proposal.criteria}
    unknown = [c.key for c in data.criteria if c.key not in known]
    if unknown:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT,
                            {"code": "UNKNOWN_CRITERION", "criteria": unknown})
    if data.verdict == ReviewVerdict.accepted:
        met = {c.key for c in data.criteria if c.verdict == "met"}
        missing = [k for k in _required_keys(package, proposal) if k not in met]
        if missing:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT,
                                {"code": "CRITERIA_NOT_MET", "criteria": missing})

    review = Review(
        proposal_id=proposal.id, reviewer_id=user.id, verdict=data.verdict,
        criteria=[c.model_dump() for c in data.criteria], rationale=data.rationale,
    )
    session.add(review)
    await session.flush()
    proposal.status = _VERDICT_STATUS[data.verdict]
    await _audit(session, task, user, "review", review.id, "created", after={
        "proposal_id": str(proposal.id), "proposal_version": proposal.version,
        "verdict": data.verdict.value, "rationale": data.rationale,
    })
    await _recompute_state(session, task)
    await notification_service.notify(
        session, recipient_id=proposal.author_id,
        event_type=NotificationEventType.review_completed,
        entity_type=NotificationEntityType.result_proposal, entity_id=proposal.id,
        task_id=task.id,
        message=f"Проверка {task.key} (версия {proposal.version}): {_VERDICT_TEXT[data.verdict]}",
    )
    await session.commit()
    await session.refresh(review)
    return review


_VERDICT_TEXT = {
    ReviewVerdict.accepted: "принято",
    ReviewVerdict.changes_requested: "на доработку",
    ReviewVerdict.rejected: "отклонено",
}


# ── Delivery and recipient acceptance (TT-17) ────────────────────────────────

async def propose_delivery(
    session: AsyncSession, task_id: uuid.UUID, data: DeliveryCreate, user: User
) -> Task:
    task = await get_task(session, task_id, user, for_update=True)
    member = await require_writer(session, task.project_id, user)
    if task.assignee_id != user.id and not has_role(member, ProjectMemberRole.manager):
        raise HTTPException(status.HTTP_403_FORBIDDEN, {"code": "PERMISSION_DENIED"})
    accepted = await session.scalar(
        select(ResultProposal).where(
            ResultProposal.task_id == task.id, ResultProposal.status == ProposalStatus.accepted,
        ).order_by(ResultProposal.version.desc()).limit(1)
    )
    if accepted is None:
        raise HTTPException(status.HTTP_409_CONFLICT, {"code": "RESULT_NOT_ACCEPTED"})
    before = task.delivery
    task.delivery = {
        "proposal_id": str(accepted.id), "target": data.target, "ref": data.ref, "note": data.note,
        "proposed_by": str(user.id), "proposed_at": datetime.now(UTC).isoformat(),
    }
    task.recipient_acceptance = None  # a new delivery awaits its own acceptance
    task.version += 1
    await _audit(session, task, user, "delivery", task.id, "proposed", before=before, after=task.delivery)
    await session.commit()
    return await get_task(session, task.id, user)


async def record_recipient_acceptance(
    session: AsyncSession, task_id: uuid.UUID, data: RecipientAcceptanceCreate, user: User
) -> Task:
    """Records the recipient's decision as a received fact; TaskTrack does not accept on their behalf."""
    task = await get_task(session, task_id, user, for_update=True)
    await require_manager(session, task.project_id, user)
    if task.delivery is None:
        raise HTTPException(status.HTTP_409_CONFLICT, {"code": "DELIVERY_NOT_PROPOSED"})
    task.recipient_acceptance = {
        **audit_service.snapshot(data, ("accepted_by", "accepted_at", "source", "ref", "note")),
        "recorded_by": str(user.id), "recorded_at": datetime.now(UTC).isoformat(),
    }
    task.version += 1
    await _audit(session, task, user, "recipient_acceptance", task.id, "recorded",
                 after=task.recipient_acceptance)
    await session.commit()
    return await get_task(session, task.id, user)


# ── Reviewer profile ─────────────────────────────────────────────────────────

async def update_member(
    session: AsyncSession, project_id: uuid.UUID, user_id: uuid.UUID, data: MemberUpdate, user: User
) -> ProjectMember:
    await require_manager(session, project_id, user)
    target = await get_member(session, project_id, user_id)
    if target is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, {"code": "PROJECT_MEMBER_NOT_FOUND"})
    before = audit_service.snapshot(target, ("role", "is_reviewer"))
    if data.role is not None:
        target.role = ProjectMemberRole(data.role)
    if data.is_reviewer is not None:
        target.is_reviewer = data.is_reviewer
    changed_before, changed_after = audit_service.diff(
        before, audit_service.snapshot(target, ("role", "is_reviewer"))
    )
    await audit_service.record(
        session, actor_id=user.id, project_id=project_id, entity_type="project_member",
        entity_id=user_id, action="updated", before=changed_before, after=changed_after,
    )
    await session.commit()
    return target


async def validate_designated_reviewer(
    session: AsyncSession, task: Task, reviewer_id: uuid.UUID | None, user: User
) -> None:
    """Called by task_service when reviewer_id changes: manager only, reviewer profile required."""
    await require_manager(session, task.project_id, user)
    if reviewer_id is None:
        return
    member = await get_member(session, task.project_id, reviewer_id)
    if member is None or not member.is_reviewer:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, {"code": "NOT_REVIEWER"})
    if reviewer_id == task.assignee_id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, {"code": "SELF_REVIEW"})


# ── Internal ─────────────────────────────────────────────────────────────────

async def recompute_state(session: AsyncSession, task: Task) -> None:
    await _recompute_state(session, task)


async def _recompute_state(session: AsyncSession, task: Task) -> None:
    await session.flush()
    statuses = set((await session.scalars(
        select(ResultProposal.status).where(
            ResultProposal.task_id == task.id, ResultProposal.status.in_(_LIVE),
        )
    )).all())
    for candidate, state in (
        (ProposalStatus.accepted, "accepted"),
        (ProposalStatus.submitted, "proposed"),
        (ProposalStatus.changes_requested, "changes_requested"),
        (ProposalStatus.rejected, "rejected"),
        (ProposalStatus.historical, "historical"),
    ):
        if candidate in statuses:
            new = state
            break
    else:
        new = "none"
    if task.result_state != new:
        task.result_state = new
        task.version += 1


async def _require_reviewer(
    session: AsyncSession, task: Task, proposal: ResultProposal, user: User
) -> None:
    member = await require_writer(session, task.project_id, user)
    if user.id in (proposal.author_id, task.assignee_id):
        raise HTTPException(status.HTTP_403_FORBIDDEN, {"code": "SELF_REVIEW"})
    if not member.is_reviewer:
        raise HTTPException(status.HTTP_403_FORBIDDEN, {"code": "NOT_REVIEWER"})
    if task.reviewer_id is not None and task.reviewer_id != user.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, {"code": "NOT_DESIGNATED_REVIEWER"})


async def _load_for_update(
    session: AsyncSession, proposal_id: uuid.UUID, user: User
) -> tuple[ResultProposal, Task]:
    proposal = await session.get(ResultProposal, proposal_id)
    if proposal is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, {"code": "PROPOSAL_NOT_FOUND"})
    # Lock order task → proposal, same as submit_proposal.
    task = await get_task(session, proposal.task_id, user, for_update=True)
    proposal = await session.scalar(
        select(ResultProposal).where(ResultProposal.id == proposal_id)
        .with_for_update().execution_options(populate_existing=True)
    )
    return proposal, task


async def _resolve_package(
    session: AsyncSession, task: Task, package_id: uuid.UUID | None
) -> WorkPackage | None:
    if package_id is None:
        if task.work_package_version is None:
            return None
        return await session.scalar(select(WorkPackage).where(
            WorkPackage.task_id == task.id, WorkPackage.version == task.work_package_version,
        ))
    package = await session.get(WorkPackage, package_id)
    if package is None or package.task_id != task.id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, {"code": "WORK_PACKAGE_NOT_FOUND"})
    return package


def _criteria_keys(package: WorkPackage | None) -> set[str] | None:
    if package is None:
        return None
    return {c["key"] for c in package.content.get("criteria", [])}


def _required_keys(package: WorkPackage | None, proposal: ResultProposal) -> list[str]:
    if package is not None:
        return [c["key"] for c in package.content.get("criteria", []) if c.get("required", True)]
    return [c["key"] for c in proposal.criteria]


async def _audit(
    session: AsyncSession, task: Task, user: User, entity_type: str, entity_id: uuid.UUID,
    action: str, before: dict | None = None, after: dict | None = None,
) -> None:
    await audit_service.record(
        session, actor_id=user.id, project_id=task.project_id, task_id=task.id,
        entity_type=entity_type, entity_id=entity_id, action=action, before=before, after=after,
    )
