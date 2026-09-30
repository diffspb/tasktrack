"""Work proposals from external sources (ADR-024, FR-003 TT-19/20).

A proposal is not a ResultProposal: it suggests work, it does not present a result.
Import never creates a task ready for execution and never allocates a resource; the
target project's manager decides. The key is (project, stage, work kind, basis identity
without revision, work_scope_key): a repeat changes nothing, a new basis revision is a new
version of the same proposal.
"""
import uuid
from datetime import UTC, datetime

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.external import ExternalObject
from app.models.portfolio import TaskBasis, WorkProposal, WorkProposalVersion
from app.models.user import User
from app.schemas.external import WorkProposalDecide, WorkProposalImport
from app.schemas.task import TaskCreate
from app.services import audit_service, external_service, portfolio_service, task_service
from app.services.external_service import identity, object_view
from app.services.permissions import require_manager, require_project_access

FINAL = ("converted", "linked", "merged", "rejected")


def _http(code: int, error: str, **extra) -> HTTPException:
    return HTTPException(code, {"code": error, **extra})


async def import_proposal(
    session: AsyncSession, project_id: uuid.UUID, data: WorkProposalImport, user: User,
) -> dict:
    await external_service.require_import_rights(session, project_id, user)
    await require_project_access(session, project_id, user)
    provider = await external_service.get_provider(session, data.provider, for_import=True)
    holder: dict = {}

    async def apply():
        basis = await external_service.require_object(session, data.basis)
        await _require_revision(session, basis, data.basis.revision)
        plan = None
        if data.verification_plan is not None:
            plan = await external_service.require_object(session, data.verification_plan)
            await _require_revision(session, plan, data.verification_plan.revision)

        proposal = await session.scalar(select(WorkProposal).where(
            WorkProposal.project_id == project_id, WorkProposal.stage == data.stage,
            WorkProposal.work_kind == data.work_kind, WorkProposal.basis_object_id == basis.id,
            WorkProposal.work_scope_key == data.work_scope_key,
        ).with_for_update())
        created = proposal is None
        if created:
            proposal = WorkProposal(project_id=project_id, stage=data.stage, work_kind=data.work_kind,
                                    basis_object_id=basis.id, work_scope_key=data.work_scope_key,
                                    status="open", current_version=0)
            session.add(proposal)
            await session.flush()
        existing = await session.scalar(select(WorkProposalVersion).where(
            WorkProposalVersion.proposal_id == proposal.id,
            WorkProposalVersion.basis_revision == data.basis.revision,
        ))
        new_version = existing is None
        if new_version:
            proposal.current_version += 1
            session.add(WorkProposalVersion(
                proposal_id=proposal.id, version=proposal.current_version, basis_revision=data.basis.revision,
                verification_plan_object_id=plan.id if plan else None,
                verification_plan_revision=data.verification_plan.revision if plan else None,
                expected_output=data.expected_output, result_scope=data.result_scope, reason=data.reason,
                registered_by=user.id,
            ))
            if not created and proposal.status != "open":
                proposal.updated_since_decision = True   # shown to the manager, never reopens by itself
            await session.flush()
            await _audit(session, proposal, user, "created" if created else "new_version",
                         after={"basis": identity(basis), "revision": data.basis.revision,
                                "version": proposal.current_version, "work_kind": data.work_kind,
                                "work_scope_key": data.work_scope_key, "stage": data.stage})
            if not created and proposal.task_id is not None:
                await _impact_for_task(session, proposal.task_id, basis, data.basis.revision, user)
        holder["proposal"] = proposal
        outcome = {"proposal_id": str(proposal.id), "created": created, "new_version": new_version,
                   "version": proposal.current_version}
        return outcome, basis.id, data.basis.revision

    outcome, replayed = await external_service.run_event(
        session, provider, user, event_id=data.event_id, contract_version=data.contract_version,
        kind="work_proposal", payload={**data.model_dump(mode="json"), "project_id": str(project_id)},
        apply=apply,
    )
    proposal = holder.get("proposal") or await session.get(WorkProposal, uuid.UUID(outcome["proposal_id"]))
    await session.commit()
    return {"proposal": await proposal_view(session, proposal), "created": outcome["created"] and not replayed,
            "new_version": outcome["new_version"] and not replayed, "replayed": replayed}


async def _require_revision(session: AsyncSession, obj: ExternalObject, revision: str) -> None:
    if await external_service.get_revision(session, obj, external_service.check_pinned(revision)) is None:
        raise _http(status.HTTP_422_UNPROCESSABLE_CONTENT, "REVISION_UNKNOWN", object=identity(obj), revision=revision)


async def _impact_for_task(
    session: AsyncSession, task_id: uuid.UUID, basis_obj: ExternalObject, revision: str, user: User,
) -> None:
    rows = (await session.scalars(select(TaskBasis).where(
        TaskBasis.task_id == task_id, TaskBasis.object_id == basis_obj.id,
        TaskBasis.role.in_(portfolio_service.IMPACT_ROLES), TaskBasis.revision != revision,
    ))).all()
    for basis in rows:
        await portfolio_service.ensure_assessment(session, basis, basis_obj, revision, user)


async def list_proposals(
    session: AsyncSession, project_id: uuid.UUID, user: User, status_filter: str | None = None,
) -> list[dict]:
    await require_project_access(session, project_id, user)
    stmt = select(WorkProposal).where(WorkProposal.project_id == project_id).order_by(WorkProposal.created_at)
    if status_filter:
        stmt = stmt.where(WorkProposal.status == status_filter)
    return [await proposal_view(session, p) for p in (await session.scalars(stmt)).all()]


async def get_proposal(session: AsyncSession, proposal_id: uuid.UUID, user: User) -> dict:
    proposal = await _load(session, proposal_id, user)
    return await proposal_view(session, proposal)


async def _load(session: AsyncSession, proposal_id: uuid.UUID, user: User, *, for_update: bool = False) -> WorkProposal:
    stmt = select(WorkProposal).where(WorkProposal.id == proposal_id)
    if for_update:
        stmt = stmt.with_for_update()
    proposal = await session.scalar(stmt)
    if proposal is None:
        raise _http(status.HTTP_404_NOT_FOUND, "WORK_PROPOSAL_NOT_FOUND")
    await require_project_access(session, proposal.project_id, user)
    return proposal


async def proposal_view(session: AsyncSession, proposal: WorkProposal) -> dict:
    basis = await session.get(ExternalObject, proposal.basis_object_id)
    versions = (await session.scalars(select(WorkProposalVersion).where(
        WorkProposalVersion.proposal_id == proposal.id).order_by(WorkProposalVersion.version))).all()
    return {
        **{c: getattr(proposal, c) for c in (
            "id", "project_id", "stage", "work_kind", "work_scope_key", "status", "task_id", "merged_into_id",
            "decision_reason", "decided_by", "decided_at", "current_version", "updated_since_decision", "created_at",
        )},
        "basis": object_view(basis), "versions": list(versions),
    }


async def decide(session: AsyncSession, proposal_id: uuid.UUID, data: WorkProposalDecide, user: User) -> dict:
    proposal = await _load(session, proposal_id, user, for_update=True)
    await require_manager(session, proposal.project_id, user)
    if proposal.status in FINAL:
        raise _http(status.HTTP_409_CONFLICT, "WORK_PROPOSAL_ALREADY_DECIDED", status=proposal.status)
    if data.action in ("merge", "defer", "reject") and not data.reason:
        raise _http(status.HTTP_422_UNPROCESSABLE_CONTENT, "REASON_REQUIRED")
    version = await session.scalar(select(WorkProposalVersion).where(
        WorkProposalVersion.proposal_id == proposal.id, WorkProposalVersion.version == proposal.current_version,
    ))
    basis_obj = await session.get(ExternalObject, proposal.basis_object_id)

    if data.action == "create_task":
        # The new task starts in its initial status; in portfolio mode it is not ready
        # until its package, inputs and grant exist — import never allocates a resource.
        task = await task_service.create_task(session, proposal.project_id, TaskCreate(
            title=data.title or f"{proposal.work_kind}: {basis_obj.type}/{basis_obj.ext_id} ({proposal.work_scope_key})",
            description=f"{version.expected_output}\n\nПричина: {version.reason}",
            task_type_key=data.task_type_key,
        ), user)
        proposal.task_id, proposal.status = task.id, "converted"
        await _cause_basis(session, task.id, basis_obj, version, proposal, user)
    elif data.action == "link":
        if data.task_id is None:
            raise _http(status.HTTP_422_UNPROCESSABLE_CONTENT, "TASK_ID_REQUIRED")
        task = await task_service.get_task(session, data.task_id, user)
        if task.project_id != proposal.project_id:
            raise _http(status.HTTP_422_UNPROCESSABLE_CONTENT, "TASK_OF_OTHER_PROJECT")
        proposal.task_id, proposal.status = task.id, "linked"
        await _cause_basis(session, task.id, basis_obj, version, proposal, user)
    elif data.action == "merge":
        if data.merge_into_id is None or data.merge_into_id == proposal.id:
            raise _http(status.HTTP_422_UNPROCESSABLE_CONTENT, "MERGE_TARGET_REQUIRED")
        target = await _load(session, data.merge_into_id, user)
        if target.project_id != proposal.project_id:
            raise _http(status.HTTP_422_UNPROCESSABLE_CONTENT, "MERGE_TARGET_OF_OTHER_PROJECT")
        proposal.merged_into_id, proposal.status = target.id, "merged"
    elif data.action == "defer":
        proposal.status = "deferred"
    else:
        proposal.status = "rejected"

    proposal.decision_reason = data.reason
    proposal.decided_by, proposal.decided_at = user.id, datetime.now(UTC)
    proposal.updated_since_decision = False
    await _audit(session, proposal, user, "decided", after={
        "action": data.action, "reason": data.reason, "task_id": str(proposal.task_id) if proposal.task_id else None,
        "merged_into_id": str(proposal.merged_into_id) if proposal.merged_into_id else None,
        "version": proposal.current_version,
    })
    await session.commit()
    return await proposal_view(session, proposal)


async def _cause_basis(
    session: AsyncSession, task_id: uuid.UUID, basis_obj: ExternalObject, version: WorkProposalVersion,
    proposal: WorkProposal, user: User,
) -> None:
    exists = await session.scalar(select(TaskBasis.id).where(
        TaskBasis.task_id == task_id, TaskBasis.object_id == basis_obj.id, TaskBasis.role == "cause",
    ))
    if exists is None:
        session.add(TaskBasis(
            task_id=task_id, object_id=basis_obj.id, revision=version.basis_revision, role="cause",
            meaning=f"предложение работы: {proposal.work_kind} / {proposal.work_scope_key}",
            freshness="pinned", created_by=user.id,
        ))
        await session.flush()


async def _audit(session: AsyncSession, proposal: WorkProposal, user: User, action: str, after: dict) -> None:
    await audit_service.record(
        session, actor_id=user.id, project_id=proposal.project_id, task_id=proposal.task_id,
        entity_type="work_proposal", entity_id=proposal.id, action=action, after=after,
    )
