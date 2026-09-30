"""Portfolio mode (ADR-024): project link (TT-08), task bases (TT-10), readiness (TT-11),
blockers and impact assessment of a new basis revision.

A project without a link is standalone: none of the external checks apply to it.
"""
import uuid
from datetime import UTC, datetime

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.external import ExternalObject, ExternalProvider, ExternalRevision
from app.models.portfolio import ImpactAssessment, ProjectPortfolioLink, TaskBasis, TaskBlocker
from app.models.project import Project, ProjectMemberRole
from app.models.session import SessionCheckpoint
from app.models.task import Task
from app.models.user import User
from app.schemas.external import BasisCreate, BlockerCreate, BlockerResolve, ImpactDecision, PortfolioLinkSet
from app.services import audit_service, external_service
from app.services.external_service import identity, object_view, same_identity
from app.services.permissions import has_role, require_manager, require_role, require_writer
from app.services.task_service import get_task

GRANT_TYPES = ("allocation", "authorization")
# Roles whose new revision needs the manager's impact decision. A grant is checked live.
IMPACT_ROLES = ("cause", "input", "normative")


def _http(code: int, error: str, **extra) -> HTTPException:
    return HTTPException(code, {"code": error, **extra})


# ── TT-08: project link ──────────────────────────────────────────────────────

async def get_link(session: AsyncSession, project_id: uuid.UUID) -> ProjectPortfolioLink | None:
    return await session.get(ProjectPortfolioLink, project_id)


async def link_view(session: AsyncSession, link: ProjectPortfolioLink) -> dict:
    office = await session.get(ExternalObject, link.office_project_object_id)
    regulation = await session.get(ExternalObject, link.regulation_object_id) if link.regulation_object_id else None
    return {
        "project_id": link.project_id, "office_project": object_view(office),
        "repository_url": link.repository_url,
        "regulation": object_view(regulation) if regulation else None,
        "regulation_revision": link.regulation_revision, "stage": link.stage,
        "is_training": link.is_training, "recipient": recipient_label(office), "created_at": link.created_at,
    }


def recipient_label(office: ExternalObject | None, project: Project | None = None) -> str:
    """How facts address the project as a recipient (ADR-024, decision 2)."""
    if office is not None:
        return f"{office.provider.key}/{office.namespace}/project/{office.ext_id}"
    return f"tasktrack:{project.key}"


async def get_project_link(session: AsyncSession, project_id: uuid.UUID, user: User) -> dict | None:
    await require_role(session, project_id, user, ProjectMemberRole.viewer)
    link = await get_link(session, project_id)
    return await link_view(session, link) if link else None


async def set_link(session: AsyncSession, project_id: uuid.UUID, data: PortfolioLinkSet, user: User) -> dict:
    """Enables portfolio mode. Linking never launches the office project, nor changes tasks."""
    if not user.is_superuser:
        await require_role(session, project_id, user, ProjectMemberRole.admin)
    provider = await external_service.get_provider(session, data.office_project.provider)
    if provider.is_training and not data.is_training:
        raise _http(status.HTTP_422_UNPROCESSABLE_CONTENT, "TRAINING_PROVIDER_FOR_REAL_PROJECT")
    office = await external_service.get_or_create_object(
        session, provider, data.office_project.namespace, "project", data.office_project.id,
    )
    regulation = None
    if data.regulation is not None:
        regulation = await external_service.require_object(session, data.regulation)
        if regulation.type != "regulation":
            raise _http(status.HTTP_422_UNPROCESSABLE_CONTENT, "NOT_A_REGULATION")
        await _require_pinned_revision(session, regulation, data.regulation.revision)
        if regulation.provider.is_training and not data.is_training:
            raise _http(status.HTTP_422_UNPROCESSABLE_CONTENT, "TRAINING_PROVIDER_FOR_REAL_PROJECT")

    link = await get_link(session, project_id)
    taken = await session.scalar(select(ProjectPortfolioLink.project_id).where(
        ProjectPortfolioLink.office_project_object_id == office.id, ProjectPortfolioLink.project_id != project_id,
    ))
    if taken is not None:
        raise _http(status.HTTP_409_CONFLICT, "OFFICE_PROJECT_ALREADY_LINKED")
    before = audit_service.snapshot(link, _LINK_FIELDS) if link else None
    if link is None:
        link = ProjectPortfolioLink(project_id=project_id, enabled_by=user.id, office_project_object_id=office.id,
                                    repository_url=data.repository_url)
        session.add(link)
    link.office_project_object_id = office.id
    link.repository_url = data.repository_url
    link.regulation_object_id = regulation.id if regulation else None
    link.regulation_revision = data.regulation.revision if data.regulation else None
    link.stage = data.stage
    link.is_training = data.is_training
    try:
        await session.flush()
    except IntegrityError:
        await session.rollback()
        raise _http(status.HTTP_409_CONFLICT, "OFFICE_PROJECT_ALREADY_LINKED")
    await audit_service.record(
        session, actor_id=user.id, project_id=project_id, entity_type="portfolio_link", entity_id=project_id,
        action="set", before=before, after=audit_service.snapshot(link, _LINK_FIELDS),
    )
    await session.commit()
    return await link_view(session, link)


async def remove_link(session: AsyncSession, project_id: uuid.UUID, user: User) -> None:
    """Back to standalone mode; bases, facts and history stay."""
    if not user.is_superuser:
        await require_role(session, project_id, user, ProjectMemberRole.admin)
    link = await get_link(session, project_id)
    if link is None:
        raise _http(status.HTTP_404_NOT_FOUND, "PORTFOLIO_LINK_NOT_FOUND")
    before = audit_service.snapshot(link, _LINK_FIELDS)
    await session.delete(link)
    await audit_service.record(
        session, actor_id=user.id, project_id=project_id, entity_type="portfolio_link", entity_id=project_id,
        action="removed", before=before,
    )
    await session.commit()


_LINK_FIELDS = ("office_project_object_id", "repository_url", "regulation_object_id",
                "regulation_revision", "stage", "is_training")


async def _require_pinned_revision(session: AsyncSession, obj: ExternalObject, revision: str) -> ExternalRevision:
    row = await external_service.get_revision(session, obj, revision)
    if row is None:
        raise _http(status.HTTP_422_UNPROCESSABLE_CONTENT, "REVISION_UNKNOWN", object=identity(obj), revision=revision)
    if row.sha256 is None:
        raise _http(status.HTTP_422_UNPROCESSABLE_CONTENT, "REVISION_NOT_PINNED", object=identity(obj),
                    revision=revision)
    return row


# ── TT-10: task bases ────────────────────────────────────────────────────────

async def _require_commissioner(session: AsyncSession, task: Task, user: User) -> None:
    member = await require_writer(session, task.project_id, user)
    if task.reporter_id != user.id and not has_role(member, ProjectMemberRole.manager):
        raise _http(status.HTTP_403_FORBIDDEN, "PERMISSION_DENIED")


async def list_bases(session: AsyncSession, task_id: uuid.UUID, user: User) -> list[dict]:
    await get_task(session, task_id, user)
    return [await basis_view(session, b) for b in await _bases(session, task_id)]


async def _bases(session: AsyncSession, task_id: uuid.UUID) -> list[TaskBasis]:
    return list((await session.scalars(
        select(TaskBasis).where(TaskBasis.task_id == task_id).order_by(TaskBasis.created_at)
    )).all())


async def basis_view(session: AsyncSession, basis: TaskBasis) -> dict:
    obj = await session.get(ExternalObject, basis.object_id)
    rev = await external_service.get_revision(session, obj, basis.revision)
    return {
        "id": basis.id, "task_id": basis.task_id, "object": object_view(obj), "revision": basis.revision,
        "role": basis.role, "meaning": basis.meaning, "freshness": basis.freshness,
        "verified": bool(rev and rev.verified), "created_at": basis.created_at,
        "evidence": await evidence_for(session, obj) if obj.type == "requirement" else [],
    }


async def evidence_for(session: AsyncSession, obj: ExternalObject) -> list[ExternalRevision]:
    """Received evidence about a requirement (compliance conclusions, CI checks, releases).
    TaskTrack shows it; it never derives compliance from its own Done."""
    rows = await session.scalars(
        select(ExternalRevision).join(ExternalObject, ExternalObject.id == ExternalRevision.object_id)
        .where(ExternalObject.type == "evidence", ExternalRevision.claims["subject"]["id"].astext == obj.ext_id)
        .order_by(ExternalRevision.observed_at)
    )
    return [r for r in rows if same_identity({k: v for k, v in (r.claims.get("subject") or {}).items()
                                              if k in ("provider", "namespace", "type", "id")}, obj)]


async def add_basis(session: AsyncSession, task_id: uuid.UUID, data: BasisCreate, user: User) -> dict:
    task = await get_task(session, task_id, user, for_update=True)
    await _require_commissioner(session, task, user)
    obj = await external_service.require_object(session, data.object)
    await _require_pinned_revision(session, obj, external_service.check_pinned(data.revision))
    if (data.role == "grant") != (obj.type in GRANT_TYPES):
        raise _http(status.HTTP_422_UNPROCESSABLE_CONTENT, "BASIS_ROLE_TYPE_MISMATCH",
                    role=data.role, type=obj.type)
    basis = TaskBasis(task_id=task.id, object_id=obj.id, revision=data.revision, role=data.role,
                      meaning=data.meaning, freshness=data.freshness, created_by=user.id)
    session.add(basis)
    try:
        await session.flush()
    except IntegrityError:
        await session.rollback()
        raise _http(status.HTTP_409_CONFLICT, "BASIS_EXISTS")
    await _audit(session, task, user, "task_basis", basis.id, "added",
                 after={"object": identity(obj), "revision": data.revision, "role": data.role,
                        "freshness": data.freshness, "meaning": data.meaning})
    await session.commit()
    return await basis_view(session, basis)


async def remove_basis(session: AsyncSession, basis_id: uuid.UUID, user: User) -> None:
    basis = await session.get(TaskBasis, basis_id)
    if basis is None:
        raise _http(status.HTTP_404_NOT_FOUND, "BASIS_NOT_FOUND")
    task = await get_task(session, basis.task_id, user, for_update=True)
    await _require_commissioner(session, task, user)
    obj = await session.get(ExternalObject, basis.object_id)
    await _audit(session, task, user, "task_basis", basis.id, "removed",
                 before={"object": identity(obj), "revision": basis.revision, "role": basis.role})
    await session.delete(basis)
    await session.commit()


async def pinned_bases(session: AsyncSession, task_id: uuid.UUID) -> list[dict]:
    """The bases as pinned into an issued WorkPackage version."""
    result = []
    for b in await _bases(session, task_id):
        obj = await session.get(ExternalObject, b.object_id)
        result.append({**identity(obj), "revision": b.revision, "role": b.role,
                       "meaning": b.meaning, "freshness": b.freshness})
    return sorted(result, key=lambda x: (x["role"], x["provider"], x["namespace"], x["type"], x["id"]))


# ── Blockers ─────────────────────────────────────────────────────────────────

async def add_blocker(session: AsyncSession, task_id: uuid.UUID, data: BlockerCreate, user: User) -> TaskBlocker:
    task = await get_task(session, task_id, user, for_update=True)
    await require_manager(session, task.project_id, user)
    blocker = await _create_blocker(session, task, user, data.reason, "manual")
    await session.commit()
    return blocker


async def _create_blocker(session: AsyncSession, task: Task, user: User, reason: str, source: str) -> TaskBlocker:
    blocker = TaskBlocker(task_id=task.id, reason=reason, source=source, created_by=user.id)
    session.add(blocker)
    await session.flush()
    await _audit(session, task, user, "task_blocker", blocker.id, "added", after={"reason": reason, "source": source})
    return blocker


async def resolve_blocker(session: AsyncSession, blocker_id: uuid.UUID, data: BlockerResolve, user: User) -> TaskBlocker:
    blocker = await session.get(TaskBlocker, blocker_id)
    if blocker is None:
        raise _http(status.HTTP_404_NOT_FOUND, "BLOCKER_NOT_FOUND")
    task = await get_task(session, blocker.task_id, user, for_update=True)
    await require_manager(session, task.project_id, user)
    if blocker.resolved_at is not None:
        raise _http(status.HTTP_409_CONFLICT, "BLOCKER_ALREADY_RESOLVED")
    blocker.resolved_at, blocker.resolved_by, blocker.resolution = datetime.now(UTC), user.id, data.resolution
    await _audit(session, task, user, "task_blocker", blocker.id, "resolved", after={"resolution": data.resolution})
    await session.commit()
    return blocker


async def list_blockers(session: AsyncSession, task_id: uuid.UUID, user: User) -> list[TaskBlocker]:
    await get_task(session, task_id, user)
    return list((await session.scalars(
        select(TaskBlocker).where(TaskBlocker.task_id == task_id).order_by(TaskBlocker.created_at)
    )).all())


# ── Impact assessment of a new basis revision ────────────────────────────────

async def on_current_changed(session: AsyncSession, obj: ExternalObject, new_revision: str, user: User) -> None:
    """A basis the task depends on got a new current revision: the manager decides; an
    active session gets a visible problem and a checkpoint. Nothing is stopped by code."""
    bases = (await session.scalars(select(TaskBasis).where(
        TaskBasis.object_id == obj.id, TaskBasis.role.in_(IMPACT_ROLES), TaskBasis.revision != new_revision,
    ))).all()
    for basis in bases:
        await ensure_assessment(session, basis, obj, new_revision, user)


async def ensure_assessment(
    session: AsyncSession, basis: TaskBasis, obj: ExternalObject, new_revision: str, user: User,
) -> ImpactAssessment | None:
    exists = await session.scalar(select(ImpactAssessment.id).where(
        ImpactAssessment.basis_id == basis.id, ImpactAssessment.new_revision == new_revision,
    ))
    if exists is not None:
        return None
    task = await session.get(Task, basis.task_id)
    if task is None or task.deleted_at is not None:
        return None
    assessment = ImpactAssessment(task_id=task.id, basis_id=basis.id, object_id=obj.id,
                                  old_revision=basis.revision, new_revision=new_revision)
    session.add(assessment)
    await session.flush()
    await _audit(session, task, user, "impact_assessment", assessment.id, "opened",
                 after={"object": identity(obj), "old_revision": basis.revision, "new_revision": new_revision})
    await _notify_active_session(
        session, task,
        f"Новая редакция основания {obj.type}/{obj.ext_id}: {basis.revision} → {new_revision}. "
        "Требуется оценка влияния руководителем.",
        {"kind": "impact_assessment", "assessment_id": str(assessment.id)},
    )
    return assessment


async def _notify_active_session(session: AsyncSession, task: Task, note: str, data: dict) -> None:
    from app.services.session_service import active_executor

    active = await active_executor(session, task.id)
    if active is not None:
        session.add(SessionCheckpoint(session_id=active.id, note=note, data=data))
        await session.flush()


async def list_assessments(session: AsyncSession, task_id: uuid.UUID, user: User) -> list[ImpactAssessment]:
    await get_task(session, task_id, user)
    return list((await session.scalars(
        select(ImpactAssessment).where(ImpactAssessment.task_id == task_id).order_by(ImpactAssessment.created_at)
    )).all())


async def decide_assessment(
    session: AsyncSession, assessment_id: uuid.UUID, data: ImpactDecision, user: User,
) -> ImpactAssessment:
    """continue — keep the old revision (rationale and authority required); reissue — move
    the basis to the new revision, the package must be reissued; recheck — the same plus a
    blocker until the repeated check is done; stop — a blocker."""
    assessment = await session.get(ImpactAssessment, assessment_id)
    if assessment is None:
        raise _http(status.HTTP_404_NOT_FOUND, "IMPACT_ASSESSMENT_NOT_FOUND")
    task = await get_task(session, assessment.task_id, user, for_update=True)
    await require_manager(session, task.project_id, user)
    if assessment.status != "pending":
        raise _http(status.HTTP_409_CONFLICT, "IMPACT_ALREADY_DECIDED")
    if data.decision == "continue" and not data.authority:
        raise _http(status.HTTP_422_UNPROCESSABLE_CONTENT, "AUTHORITY_REQUIRED")
    basis = await session.get(TaskBasis, assessment.basis_id)
    obj = await session.get(ExternalObject, assessment.object_id)
    if data.decision in ("reissue", "recheck"):
        basis.revision = assessment.new_revision
    if data.decision == "recheck":
        await _create_blocker(session, task, user,
                              f"Повторная проверка по редакции {assessment.new_revision} "
                              f"основания {obj.type}/{obj.ext_id}", "impact_decision")
    if data.decision == "stop":
        await _create_blocker(session, task, user, f"Работа остановлена по оценке влияния: {data.rationale}",
                              "impact_decision")
        await _notify_active_session(session, task, f"Руководитель остановил работу: {data.rationale}",
                                     {"kind": "impact_decision", "assessment_id": str(assessment.id)})
    assessment.status, assessment.decision = "decided", data.decision
    assessment.rationale, assessment.authority = data.rationale, data.authority
    assessment.decided_by, assessment.decided_at = user.id, datetime.now(UTC)
    await _audit(session, task, user, "impact_assessment", assessment.id, "decided",
                 after=data.model_dump())
    await session.commit()
    return assessment


# ── TT-11: readiness ─────────────────────────────────────────────────────────

def _reason(code: str, message: str, basis: TaskBasis | None = None, obj: ExternalObject | None = None,
            revision: str | None = None, as_of: datetime | None = None) -> dict:
    return {"code": code, "message": message, "basis_id": basis.id if basis else None,
            "object": identity(obj) if obj else None, "revision": revision, "as_of": as_of}


def _parse_time(value) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)


async def _fact_problem(
    session: AsyncSession, obj: ExternalObject, rev: ExternalRevision | None, link: ProjectPortfolioLink,
) -> tuple[str, str] | None:
    """Why a received fact cannot satisfy a readiness condition, or None."""
    provider = await session.get(ExternalProvider, obj.provider_id)
    if rev is None:
        return "FACT_UNKNOWN", "редакция не зарегистрирована"
    if not rev.verified:
        return "FACT_UNVERIFIED", "поставщик не уполномочен на этот вид фактов — это непроверенное сообщение"
    if provider.is_training and not link.is_training:
        return "FACT_TRAINING", "учебный источник не подтверждает готовность реальной работы"
    if not provider.active:
        return "PROVIDER_INACTIVE", f"поставщик {provider.key} отключён в реестре"
    if obj.status == "revoked":
        return "FACT_REVOKED", "факт отозван"
    return None


def _in_force(claims: dict, now: datetime) -> tuple[str, str] | None:
    until = _parse_time(claims.get("valid_until"))
    if until is None:
        return "GRANT_NO_TERM", "нет условия действия (valid_until)"
    if until <= now:
        return "GRANT_EXPIRED", f"срок действия истёк {until.isoformat()}"
    since = _parse_time(claims.get("valid_from"))
    if since is not None and since > now:
        return "GRANT_NOT_YET_VALID", f"действует с {since.isoformat()}"
    return None


def _recipient_matches(claim, office: ExternalObject, project: Project) -> bool:
    return same_identity(claim, office) or claim == f"tasktrack:{project.key}" or claim == recipient_label(office)


async def readiness(session: AsyncSession, task: Task, *, now: datetime | None = None) -> dict:
    now = now or datetime.now(UTC)
    link = await get_link(session, task.project_id)
    if link is None:
        return {"mode": "standalone", "ready": True, "checked_at": now, "conditions": []}
    from app.services.work_package_service import current_package

    project = await session.get(Project, task.project_id)
    office = await session.get(ExternalObject, link.office_project_object_id)
    bases = await _bases(session, task.id)
    objects = {b.id: await session.get(ExternalObject, b.object_id) for b in bases}
    decided_continue = {
        (a.basis_id, a.new_revision) for a in (await session.scalars(select(ImpactAssessment).where(
            ImpactAssessment.task_id == task.id, ImpactAssessment.decision == "continue",
        ))).all()
    }
    conditions = []

    # 1. Issued package, assignee (local rights are checked by the operation itself).
    reasons = []
    package = await current_package(session, task)
    if package is None:
        reasons.append(_reason("NO_WORK_PACKAGE", "нет выданной версии задания"))
    elif package.content.get("bases", []) != await pinned_bases(session, task.id):
        reasons.append(_reason("WORK_PACKAGE_OUTDATED",
                               f"основания изменились после выпуска версии {package.version} — перевыпустите задание"))
    if task.assignee_id is None:
        reasons.append(_reason("NO_ASSIGNEE", "исполнитель не назначен"))
    conditions.append({"key": "package", "ok": not reasons, "reasons": reasons, "facts": []})

    # 2. Mandatory inputs pinned and accepted for the required use.
    reasons, facts = [], []
    for b in (b for b in bases if b.role == "input"):
        obj = objects[b.id]
        found, problems = await _input_acceptance(session, b, obj, link, office, project)
        if found is not None:
            facts.append({"basis_id": b.id, "fact": identity(found[0]), "revision": found[1].revision,
                          "as_of": found[1].observed_at, "claims": found[1].claims})
        else:
            reasons.append(_reason("INPUT_NOT_ACCEPTED",
                                   f"вход {obj.type}/{obj.ext_id}@{b.revision} не принят для использования"
                                   + (f": {problems}" if problems else ""), b, obj, b.revision))
    conditions.append({"key": "inputs", "ok": not reasons, "reasons": reasons, "facts": facts})

    # 3. Applicable normative bases accepted for this stage; research may rely on a candidate.
    reasons, facts = [], []
    research = task.task_type is not None and task.task_type.key == "research"
    if link.regulation_object_id is not None:
        reg = await session.get(ExternalObject, link.regulation_object_id)
        rev = await external_service.get_revision(session, reg, link.regulation_revision)
        problem = await _fact_problem(session, reg, rev, link)
        if problem:
            reasons.append(_reason("REGULATION_" + problem[0].removeprefix("FACT_"),
                                   f"регламент {reg.ext_id}@{link.regulation_revision}: {problem[1]}",
                                   obj=reg, revision=link.regulation_revision))
        else:
            facts.append({"regulation": identity(reg), "revision": rev.revision, "as_of": rev.observed_at})
    for b in (b for b in bases if b.role == "normative"):
        obj = objects[b.id]
        rev = await external_service.get_revision(session, obj, b.revision)
        problem = await _fact_problem(session, obj, rev, link)
        if problem:
            reasons.append(_reason("NORMATIVE_" + problem[0].removeprefix("FACT_"),
                                   f"{obj.type}/{obj.ext_id}@{b.revision}: {problem[1]}", b, obj, b.revision))
            continue
        state = rev.claims.get("status")
        allowed = {"accepted", "candidate"} if research else {"accepted"}
        if not (state in allowed or (research and obj.type == "initiative")):
            reasons.append(_reason("NORMATIVE_NOT_ACCEPTED",
                                   f"{obj.type}/{obj.ext_id}@{b.revision} не принят (status={state})"
                                   + (" — для исследования допустимы кандидат или инициатива" if research else ""),
                                   b, obj, b.revision, rev.observed_at))
            continue
        stages = rev.claims.get("stages")
        if stages is not None and link.stage is not None and link.stage not in stages:
            reasons.append(_reason("NORMATIVE_WRONG_STAGE",
                                   f"{obj.type}/{obj.ext_id}@{b.revision} принят для этапов {stages}, "
                                   f"а проект на этапе {link.stage}", b, obj, b.revision, rev.observed_at))
            continue
        facts.append({"basis_id": b.id, "object": identity(obj), "revision": b.revision,
                      "status": state, "as_of": rev.observed_at})
    conditions.append({"key": "normative", "ok": not reasons, "reasons": reasons, "facts": facts})

    # 4. An allocation or owner/office authorization for this bounded work, in force.
    grant_reasons, facts = [], []
    for b in (b for b in bases if b.role == "grant"):
        obj = objects[b.id]
        # A grant is judged by its current state; without one, by the pinned revision itself.
        rev = await external_service.get_revision(session, obj, obj.current_revision or b.revision)
        problem = await _fact_problem(session, obj, rev, link)
        if problem is None and obj.revision_state == "pending_reconciliation":
            problem = ("GRANT_STATE_UNKNOWN", "текущая редакция разрешения не сверена")
        if problem is None:
            claims = rev.claims
            missing = [f for f in ("recipient", "scope", "resource", "limit") if not claims.get(f)]
            if claims.get("status") != "granted":
                problem = ("GRANT_NOT_GRANTED", f"статус «{claims.get('status')}» — потребность без выделения не подходит")
            elif missing:
                problem = ("GRANT_INCOMPLETE", f"нет полей: {', '.join(missing)}")
            elif not _recipient_matches(claims.get("recipient"), office, project):
                problem = ("GRANT_OTHER_RECIPIENT", "разрешение выдано другому получателю")
            else:
                problem = _in_force(claims, now)
        if problem:
            code = problem[0] if problem[0].startswith(("GRANT_", "PROVIDER_")) else "GRANT_" + problem[0].removeprefix("FACT_")
            grant_reasons.append(_reason(code, f"{obj.type}/{obj.ext_id}: {problem[1]}", b, obj,
                                         obj.current_revision, rev.observed_at if rev else None))
        else:
            facts.append({"basis_id": b.id, "object": identity(obj), "revision": rev.revision,
                          "as_of": rev.observed_at, "claims": rev.claims})
    ok = bool(facts)
    if not ok and not grant_reasons:
        grant_reasons.append(_reason("NO_GRANT", "нет выделения ресурса или разрешения на этот объём работы"))
    conditions.append({"key": "grant", "ok": ok, "reasons": [] if ok else grant_reasons, "facts": facts})

    # 5. No unresolved change of a mandatory basis, revocation or registered blocker.
    reasons = []
    for blocker in (await session.scalars(select(TaskBlocker).where(
        TaskBlocker.task_id == task.id, TaskBlocker.resolved_at.is_(None),
    ))).all():
        reasons.append({**_reason("BLOCKER", blocker.reason), "basis_id": None})
    for a in (await session.scalars(select(ImpactAssessment).where(
        ImpactAssessment.task_id == task.id, ImpactAssessment.status == "pending",
    ))).all():
        obj = await session.get(ExternalObject, a.object_id)
        reasons.append(_reason("IMPACT_PENDING",
                               f"новая редакция {obj.type}/{obj.ext_id}: {a.old_revision} → {a.new_revision}, "
                               "ждёт оценки влияния", obj=obj, revision=a.new_revision))
    for b in bases:
        obj = objects[b.id]
        if b.role in IMPACT_ROLES and obj.status == "revoked":
            reasons.append(_reason("BASIS_REVOKED", f"основание {obj.type}/{obj.ext_id} отозвано", b, obj))
        if b.role in IMPACT_ROLES and b.freshness == "confirm_current":
            if obj.revision_state != "current":
                reasons.append(_reason("BASIS_STATE_UNKNOWN",
                                       f"текущее состояние {obj.type}/{obj.ext_id} не подтверждено поставщиком "
                                       f"({obj.revision_state}) — правило требует подтверждения",
                                       b, obj, obj.current_revision, obj.state_as_of))
            elif obj.current_revision != b.revision and (b.id, obj.current_revision) not in decided_continue:
                reasons.append(_reason("BASIS_CHANGED",
                                       f"текущая редакция {obj.type}/{obj.ext_id} — {obj.current_revision}, "
                                       f"задача закреплена на {b.revision}", b, obj, obj.current_revision,
                                       obj.state_as_of))
    conditions.append({"key": "blockers", "ok": not reasons, "reasons": reasons, "facts": []})

    return {"mode": "portfolio", "ready": all(c["ok"] for c in conditions), "checked_at": now,
            "conditions": conditions}


async def _input_acceptance(
    session: AsyncSession, basis: TaskBasis, obj: ExternalObject, link: ProjectPortfolioLink,
    office: ExternalObject, project: Project,
) -> tuple[tuple[ExternalObject, ExternalRevision] | None, str]:
    """Finds a usable input_acceptance fact for exactly this input revision and recipient."""
    candidates = (await session.execute(
        select(ExternalObject, ExternalRevision)
        .join(ExternalRevision, (ExternalRevision.object_id == ExternalObject.id)
              & (ExternalRevision.revision == ExternalObject.current_revision))
        .where(ExternalObject.type == "input_acceptance",
               ExternalRevision.claims["input"]["id"].astext == obj.ext_id)
    )).all()
    problems = []
    for fact, rev in candidates:
        claims = rev.claims
        inp = claims.get("input") or {}
        if not same_identity(inp, obj) or inp.get("revision") != basis.revision:
            if same_identity(inp, obj):
                problems.append(f"принята другая редакция ({inp.get('revision')})")
            continue
        problem = await _fact_problem(session, fact, rev, link)
        if problem is None and fact.revision_state == "pending_reconciliation":
            problem = ("FACT_STATE_UNKNOWN", "текущая редакция подтверждения не сверена")
        if problem:
            problems.append(problem[1])
            continue
        missing = [f for f in ("usage", "accepted_by", "accepted_at", "authority") if not claims.get(f)]
        if missing:
            problems.append(f"в подтверждении нет полей: {', '.join(missing)}")
            continue
        if not _recipient_matches(claims.get("recipient"), office, project):
            problems.append("подтверждение выдано другому получателю")
            continue
        return (fact, rev), ""
    return None, "; ".join(problems)


async def task_readiness(session: AsyncSession, task_id: uuid.UUID, user: User) -> dict:
    task = await get_task(session, task_id, user)
    return await readiness(session, task)


async def require_ready(session: AsyncSession, task: Task) -> None:
    """Gate for starting execution in portfolio mode: session claim and leaving `initial`."""
    result = await readiness(session, task)
    if not result["ready"]:
        reasons = [
            {"condition": c["key"], "code": r["code"], "message": r["message"]}
            for c in result["conditions"] if not c["ok"] for r in c["reasons"]
        ]
        raise _http(status.HTTP_409_CONFLICT, "TASK_NOT_READY", reasons=reasons)


async def _audit(
    session: AsyncSession, task: Task, user: User, entity_type: str, entity_id: uuid.UUID, action: str,
    before: dict | None = None, after: dict | None = None,
) -> None:
    await audit_service.record(
        session, actor_id=user.id, project_id=task.project_id, task_id=task.id,
        entity_type=entity_type, entity_id=entity_id, action=action, before=before, after=after,
    )
