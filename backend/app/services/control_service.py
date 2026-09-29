"""Manager's control view over open work (FR-003 TT-22).

For every open task (not in a final status) computes why it is waiting, so a
manager sees at a glance unsupported work, the review queue and stuck sessions.
Waiting reasons:
- no_work_package       — no issued assignment (draft or nothing): unsupported work
- work_package_changed  — the draft differs from the issued version: needs reissue
- no_assignee
- blocked               — a blocking link from a task that is not finished
- awaiting_review       — a result proposal waits for review
- changes_requested     — review returned the result for rework
- session_stale         — active session without checkpoints for STALE_AFTER
- awaiting_recipient    — delivery proposed, recipient's acceptance not recorded
- unverified_result     — only a historical (never reviewed) result exists
Basis and input freshness (TT-10/11) are added once the external contracts exist.
"""
import uuid
from collections import Counter
from datetime import UTC, datetime, timedelta

from sqlalchemy import select, tuple_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased, selectinload

from app.models.link_type import LinkType
from app.models.session import TaskSession
from app.models.task import Task, TaskLink
from app.models.user import User
from app.models.work_package import WorkPackage
from app.models.workflow import Status, StatusCategory
from app.services import work_package_service
from app.services.permissions import require_project_access

STALE_AFTER = timedelta(hours=24)


async def overview(
    session: AsyncSession,
    project_id: uuid.UUID,
    user: User,
    *,
    specialization: str | None = None,
    reviewer_id: uuid.UUID | None = None,
    reason: str | None = None,
) -> dict:
    await require_project_access(session, project_id, user)
    rows = (await session.execute(
        select(Task, Status)
        .join(Status, Status.id == Task.current_status_id)
        .options(selectinload(Task.task_type))
        .where(Task.project_id == project_id, Task.deleted_at.is_(None),
               Status.category != StatusCategory.final)
        .order_by(Task.created_at)
    )).all()
    tasks = [t for t, _ in rows]
    status_by_task = {t.id: st for t, st in rows}
    ids = [t.id for t in tasks]

    packages = await _current_packages(session, tasks)
    sessions = {s.task_id: s for s in (await session.scalars(select(TaskSession).where(
        TaskSession.task_id.in_(ids), TaskSession.state == "active", TaskSession.role == "executor",
    ))).all()} if ids else {}
    blockers = await _open_blockers(session, ids)
    now = datetime.now(UTC)

    items = []
    for task in tasks:
        package = packages.get(task.id)
        spec = package.content.get("specialization") if package else None
        waiting = _waiting(task, package, sessions.get(task.id), blockers.get(task.id), now)
        items.append({
            "id": str(task.id), "key": task.key, "title": task.title,
            "task_type": task.task_type.key if task.task_type else None,
            "status": status_by_task[task.id].name,
            "assignee_id": str(task.assignee_id) if task.assignee_id else None,
            "reviewer_id": str(task.reviewer_id) if task.reviewer_id else None,
            "specialization": spec,
            "work_package_version": task.work_package_version,
            "result_state": task.result_state,
            "active_session": _session_out(sessions.get(task.id), now),
            "blocked_by": blockers.get(task.id, []),
            "waiting": waiting,
        })

    summary = {
        "open_tasks": len(items),
        "by_reason": dict(Counter(r for i in items for r in i["waiting"])),
        "by_specialization": dict(Counter(i["specialization"] or "—" for i in items)),
    }
    if specialization:
        items = [i for i in items if i["specialization"] == specialization]
    if reviewer_id:
        items = [i for i in items if i["reviewer_id"] == str(reviewer_id)]
    if reason:
        items = [i for i in items if reason in i["waiting"]]
    return {"summary": summary, "items": items}


def _waiting(task: Task, package: WorkPackage | None, active: TaskSession | None,
             blocked_by: list[str] | None, now: datetime) -> list[str]:
    reasons = []
    if package is None:
        reasons.append("no_work_package")
    elif task.work_package_draft and work_package_service.normalize(task.work_package_draft) != package.content:
        reasons.append("work_package_changed")
    if task.assignee_id is None:
        reasons.append("no_assignee")
    if blocked_by:
        reasons.append("blocked")
    state_reason = {
        "proposed": "awaiting_review",
        "changes_requested": "changes_requested",
        "historical": "unverified_result",
    }.get(task.result_state)
    if state_reason:
        reasons.append(state_reason)
    if active is not None and now - (active.last_checkpoint_at or active.created_at) > STALE_AFTER:
        reasons.append("session_stale")
    if task.delivery and not task.recipient_acceptance:
        reasons.append("awaiting_recipient")
    return reasons


def _session_out(active: TaskSession | None, now: datetime) -> dict | None:
    if active is None:
        return None
    last = active.last_checkpoint_at or active.created_at
    return {
        "id": str(active.id), "user_id": str(active.user_id), "machine": active.machine,
        "started_at": active.created_at.isoformat(),
        "last_checkpoint_at": active.last_checkpoint_at.isoformat() if active.last_checkpoint_at else None,
        "silent_hours": round((now - last).total_seconds() / 3600, 1),
    }


async def _current_packages(session: AsyncSession, tasks: list[Task]) -> dict[uuid.UUID, WorkPackage]:
    keys = [(t.id, t.work_package_version) for t in tasks if t.work_package_version is not None]
    if not keys:
        return {}
    packages = (await session.scalars(select(WorkPackage).where(
        tuple_(WorkPackage.task_id, WorkPackage.version).in_(keys)
    ))).all()
    return {p.task_id: p for p in packages}


async def _open_blockers(session: AsyncSession, task_ids: list[uuid.UUID]) -> dict[uuid.UUID, list[str]]:
    """Keys of unfinished tasks that block each task via a link type with a blocking constraint."""
    if not task_ids:
        return {}
    source = aliased(Task)
    rows = (await session.execute(
        select(TaskLink.target_task_id, source.key)
        .join(LinkType, LinkType.id == TaskLink.link_type_id)
        .join(source, source.id == TaskLink.source_task_id)
        .join(Status, Status.id == source.current_status_id)
        .where(
            TaskLink.target_task_id.in_(task_ids),
            LinkType.constraint["type"].astext == "blocking",
            source.deleted_at.is_(None),
            Status.category != StatusCategory.final,
        )
    )).all()
    result: dict[uuid.UUID, list[str]] = {}
    for target, key in rows:
        result.setdefault(target, []).append(key)
    return result
