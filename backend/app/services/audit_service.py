"""Durable audit log / event journal (ADR-018, FR-003 TT-06).

Writers call `record()` before their commit, so the event is stored in the same
transaction as the change: a rolled-back command leaves no event, a committed
one always has it.

Readers call `list_events()`. Order and cursor are (xid, id), and only events of
transactions older than the reader's snapshot xmin are returned (plus the
reader's own). Every transaction that could still add an event has
xid >= xmin, so it can never land behind a cursor already handed out —
no gaps even when transactions commit out of order. Re-reading from the same
cursor returns the same events: consumers deduplicate by event id.
"""
import contextvars
import enum
import uuid
from dataclasses import dataclass
from datetime import date, datetime
from urllib.parse import unquote

from fastapi import HTTPException, status
from sqlalchemy import or_, select, text, tuple_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit import AuditEvent

MAX_REASON_LEN = 500
DEFAULT_LIMIT = 100
MAX_LIMIT = 500

# Set per request from the X-Change-Reason header (ChangeReasonMiddleware).
change_reason: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "change_reason", default=None
)

TASK_FIELDS = (
    "key", "title", "description", "priority", "task_type_id", "workflow_id",
    "current_status_id", "assignee_id", "reporter_id", "parent_task_id",
    "start_date", "due_date", "duration_days", "meta", "version",
)
COMMENT_FIELDS = ("content", "labels", "parent_comment_id", "author_id")


@dataclass
class Page:
    items: list[AuditEvent]
    next_cursor: str | None


# ── Writing ──────────────────────────────────────────────────────────────────

async def record(
    session: AsyncSession,
    *,
    actor_id: uuid.UUID | None,
    project_id: uuid.UUID | None,
    entity_type: str,
    entity_id: uuid.UUID,
    action: str,
    task_id: uuid.UUID | None = None,
    before: dict | None = None,
    after: dict | None = None,
) -> AuditEvent:
    """Add an event to the session; it is committed together with the caller's change."""
    event = AuditEvent(
        actor_id=actor_id, project_id=project_id, task_id=task_id,
        entity_type=entity_type, entity_id=entity_id, action=action,
        reason=change_reason.get(), before=before, after=after,
    )
    session.add(event)
    return event


def snapshot(obj, fields: tuple[str, ...]) -> dict:
    return {f: _jsonable(getattr(obj, f)) for f in fields}


def diff(before: dict, after: dict) -> tuple[dict, dict]:
    """Only the fields that changed, as (before, after)."""
    changed = [k for k in after if before.get(k) != after[k]]
    return {k: before.get(k) for k in changed}, {k: after[k] for k in changed}


def parse_reason_header(raw: str | None) -> str | None:
    """Header values are latin-1; clients percent-encode UTF-8 text."""
    if not raw:
        return None
    return unquote(raw).strip()[:MAX_REASON_LEN] or None


# ── Reading ──────────────────────────────────────────────────────────────────

async def list_events(
    session: AsyncSession,
    *,
    project_id: uuid.UUID | None = None,
    task_id: uuid.UUID | None = None,
    system: bool = False,
    after: str | None = None,
    limit: int = DEFAULT_LIMIT,
) -> Page:
    """Events of a project, of a task, or system-level ones (project_id IS NULL)."""
    limit = max(1, min(limit, MAX_LIMIT))
    stmt = select(AuditEvent)
    if system:
        stmt = stmt.where(AuditEvent.project_id.is_(None))
    if project_id is not None:
        stmt = stmt.where(AuditEvent.project_id == project_id)
    if task_id is not None:
        stmt = stmt.where(AuditEvent.task_id == task_id)
    if after:
        stmt = stmt.where(tuple_(AuditEvent.xid, AuditEvent.id) > tuple_(*decode_cursor(after)))

    horizon = text("(pg_snapshot_xmin(pg_current_snapshot())::text)::bigint")
    own = text("(pg_current_xact_id_if_assigned()::text)::bigint")
    stmt = (
        stmt.where(or_(AuditEvent.xid < horizon, AuditEvent.xid == own))
        .order_by(AuditEvent.xid, AuditEvent.id)
        .limit(limit)
    )
    items = list((await session.scalars(stmt)).all())
    return Page(items=items, next_cursor=encode_cursor(items[-1]) if items else after)


def encode_cursor(event: AuditEvent) -> str:
    return f"{event.xid}.{event.id}"


def decode_cursor(cursor: str) -> tuple[int, int]:
    try:
        xid, event_id = cursor.split(".")
        return int(xid), int(event_id)
    except ValueError:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, {"code": "INVALID_CURSOR"})


def _jsonable(value):
    if isinstance(value, uuid.UUID):
        return str(value)
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, enum.Enum):
        return value.value
    if isinstance(value, dict):
        return {k: _jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(v) for v in value]
    return value

