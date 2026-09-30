"""Task assignment (WorkPackage): editable draft, immutable issued versions (ADR-020, FR-003 TT-09)."""
import hashlib
import json
import uuid

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.project import Project, ProjectMemberRole
from app.models.task import Task
from app.models.user import User
from app.models.work_package import WorkPackage
from app.schemas.work_package import WorkPackageContent
from app.services import audit_service
from app.services.permissions import has_role, require_writer
from app.services.task_service import get_task

REQUIRED_FIELDS = ("goal", "expected_result", "specialization")


def normalize(content: dict) -> dict:
    """Canonical form: validated, criteria keyed c1, c2… where no key was given."""
    data = WorkPackageContent.model_validate(content).model_dump()
    taken = {c["key"] for c in data["criteria"] if c["key"]}
    n = 0
    for criterion in data["criteria"]:
        if not criterion["key"]:
            n += 1
            while f"c{n}" in taken:
                n += 1
            criterion["key"] = f"c{n}"
            taken.add(criterion["key"])
    return data


def digest(content: dict) -> str:
    canonical = json.dumps(content, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(canonical.encode()).hexdigest()


def missing_fields(content: dict) -> list[str]:
    missing = [f for f in REQUIRED_FIELDS if not (content.get(f) or "").strip()]
    if not content.get("criteria"):
        missing.append("criteria")
    return missing


async def with_bases(session: AsyncSession, task: Task, content: dict) -> dict:
    """Issued content pins the task's bases (ADR-024, TT-10); tasks without bases keep the
    previous content shape, so existing versions stay valid."""
    from app.services.portfolio_service import pinned_bases

    content = {k: v for k, v in content.items() if k != "bases"}
    bases = await pinned_bases(session, task.id)
    return {**content, "bases": bases} if bases else content


async def get_state(session: AsyncSession, task_id: uuid.UUID, user: User) -> dict:
    task = await get_task(session, task_id, user)
    current = await current_package(session, task)
    draft = task.work_package_draft
    if current is None:
        state = "draft" if draft else "none"
    else:
        expected = await with_bases(session, task, normalize(draft) if draft is not None else current.content)
        state = "issued" if expected == current.content else "draft_changed"
    return {"state": state, "draft": draft, "current": current}


async def save_draft(
    session: AsyncSession, task_id: uuid.UUID, content: WorkPackageContent, user: User
) -> dict:
    task = await get_task(session, task_id, user, for_update=True)
    await _require_editor(session, task, user)
    before = task.work_package_draft
    task.work_package_draft = content.model_dump()
    await audit_service.record(
        session, actor_id=user.id, project_id=task.project_id, task_id=task.id,
        entity_type="work_package_draft", entity_id=task.id, action="updated",
        before=before, after=task.work_package_draft,
    )
    await session.commit()
    return await get_state(session, task_id, user)


async def issue(session: AsyncSession, task_id: uuid.UUID, user: User) -> WorkPackage:
    task = await get_task(session, task_id, user, for_update=True)
    await _require_editor(session, task, user)
    if not task.work_package_draft:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT,
                            {"code": "WORK_PACKAGE_INCOMPLETE", "missing": [*REQUIRED_FIELDS, "criteria"]})
    content = normalize(task.work_package_draft)
    missing = missing_fields(content)
    if missing:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT,
                            {"code": "WORK_PACKAGE_INCOMPLETE", "missing": missing})
    content = await with_bases(session, task, content)
    current = await current_package(session, task)
    if current is not None and current.content == content:
        raise HTTPException(status.HTTP_409_CONFLICT, {"code": "WORK_PACKAGE_UNCHANGED"})

    package = WorkPackage(
        task_id=task.id, version=(task.work_package_version or 0) + 1,
        content=content, digest=digest(content), issued_by=user.id,
    )
    session.add(package)
    task.work_package_version = package.version
    task.version += 1
    await session.flush()
    await audit_service.record(
        session, actor_id=user.id, project_id=task.project_id, task_id=task.id,
        entity_type="work_package", entity_id=package.id, action="issued",
        after={"version": package.version, "digest": package.digest},
    )
    await session.commit()
    return package


async def list_versions(session: AsyncSession, task_id: uuid.UUID, user: User) -> list[WorkPackage]:
    await get_task(session, task_id, user)
    return list((await session.scalars(
        select(WorkPackage).where(WorkPackage.task_id == task_id).order_by(WorkPackage.version)
    )).all())


async def get_package(session: AsyncSession, package_id: uuid.UUID, user: User) -> WorkPackage:
    package = await session.get(WorkPackage, package_id)
    if package is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, {"code": "WORK_PACKAGE_NOT_FOUND"})
    await get_task(session, package.task_id, user)  # read access
    return package


async def export(session: AsyncSession, package_id: uuid.UUID, user: User) -> dict:
    """Pinned copy for console agents: identity, version and digest travel with the content."""
    package = await get_package(session, package_id, user)
    task = await session.get(Task, package.task_id)
    project = await session.get(Project, task.project_id)
    return {
        "id": str(package.id),
        "version": package.version,
        "digest": package.digest,
        "issued_at": package.created_at.isoformat(),
        "issued_by": str(package.issued_by),
        "project": {"id": str(project.id), "key": project.key},
        "task": {"id": str(task.id), "key": task.key, "title": task.title},
        "content": package.content,
    }


async def current_package(session: AsyncSession, task: Task) -> WorkPackage | None:
    if task.work_package_version is None:
        return None
    return await session.scalar(select(WorkPackage).where(
        WorkPackage.task_id == task.id, WorkPackage.version == task.work_package_version,
    ))


async def _require_editor(session: AsyncSession, task: Task, user: User) -> None:
    """The assignment is set by whoever commissions the work: the task's reporter or a manager."""
    member = await require_writer(session, task.project_id, user)
    if task.reporter_id != user.id and not has_role(member, ProjectMemberRole.manager):
        raise HTTPException(status.HTTP_403_FORBIDDEN, {"code": "PERMISSION_DENIED"})
