"""Safe retry of commands by Idempotency-Key (ADR-019, FR-003 TT-04).

Protocol, per (user, key):
1. `reserve()` inserts the key row inside the request transaction, before the
   command runs. The command's own commit commits the row with the change; if
   the command fails, the row is rolled back and a retry simply runs it again.
   A concurrent duplicate blocks on the primary key until the first request
   finishes, then finds its row.
2. `complete()` stores the response right after the command (separate commit).
3. A repeat with the same request gets the stored response — after write access
   to the projects the command changed is checked again. A different request
   with the same key is rejected.

A row without a response older than OUTCOME_UNKNOWN_AFTER means the command
committed but the response was lost (process crash between the two commits):
the client must read the resource instead of retrying.
"""
import asyncio
import hashlib
import string
import uuid
from datetime import UTC, datetime, timedelta

from fastapi import HTTPException, status
from sqlalchemy import delete, distinct, select, text, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit import AuditEvent
from app.models.idempotency import IdempotencyKey
from app.models.user import User
from app.services.permissions import require_writer

MUTATING_METHODS = frozenset({"POST", "PUT", "PATCH", "DELETE"})
KEY_TTL = timedelta(hours=24)
OUTCOME_UNKNOWN_AFTER = timedelta(seconds=60)
WAIT_FOR_COMPLETION = 5.0  # seconds a duplicate waits for the first request's response
_POLL_INTERVAL = 0.05
_KEY_CHARS = frozenset(string.ascii_letters + string.digits + "-_.:")


class IdempotentReplay(Exception):
    """Raised instead of running the command; converted to the stored response."""

    def __init__(self, record: IdempotencyKey):
        self.status_code = record.status_code
        self.body = record.response_body or ""
        self.media_type = record.media_type


def request_hash(method: str, path: str, body: bytes) -> str:
    return hashlib.sha256(method.encode() + b"\n" + path.encode() + b"\n" + body).hexdigest()


def validate_key(key: str) -> None:
    if not 1 <= len(key) <= 255 or not set(key) <= _KEY_CHARS:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, {"code": "IDEMPOTENCY_KEY_INVALID"})


async def reserve(session: AsyncSession, user: User, key: str, req_hash: str) -> None:
    """Reserve the key for this command, or raise IdempotentReplay / HTTPException."""
    validate_key(key)
    deadline = asyncio.get_running_loop().time() + WAIT_FOR_COMPLETION
    while True:
        inserted = await session.scalar(
            insert(IdempotencyKey)
            .values(user_id=user.id, key=key, request_hash=req_hash)
            .on_conflict_do_nothing()
            .returning(IdempotencyKey.key)
        )
        if inserted is not None:
            return

        record = await session.scalar(
            select(IdempotencyKey)
            .where(IdempotencyKey.user_id == user.id, IdempotencyKey.key == key)
            .execution_options(populate_existing=True)
        )
        if record is None:
            continue  # the other request rolled back between our two statements
        now = datetime.now(UTC)
        if now - record.created_at > KEY_TTL:
            await session.execute(delete(IdempotencyKey).where(
                IdempotencyKey.user_id == user.id, IdempotencyKey.key == key,
            ))
            continue
        if record.request_hash != req_hash:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, {"code": "IDEMPOTENCY_KEY_REUSED"})
        if record.completed_at is not None:
            await _check_replay_access(session, record, user)
            raise IdempotentReplay(record)
        if now - record.created_at > OUTCOME_UNKNOWN_AFTER:
            raise HTTPException(status.HTTP_409_CONFLICT, {"code": "IDEMPOTENCY_OUTCOME_UNKNOWN"})
        if asyncio.get_running_loop().time() > deadline:
            raise HTTPException(status.HTTP_409_CONFLICT, {"code": "IDEMPOTENCY_IN_PROGRESS"})
        # The first request committed its command and is about to store the response.
        await asyncio.sleep(_POLL_INTERVAL)


async def release(session: AsyncSession, user_id: uuid.UUID, key: str) -> None:
    """The command failed: drop an uncommitted reservation so a retry runs again.
    Not committed here — if the command did commit, the session's rollback keeps the row."""
    await session.execute(delete(IdempotencyKey).where(
        IdempotencyKey.user_id == user_id, IdempotencyKey.key == key,
        IdempotencyKey.completed_at.is_(None),
        IdempotencyKey.xid == text("(pg_current_xact_id_if_assigned()::text)::bigint"),
    ))


async def complete(
    session: AsyncSession, user_id: uuid.UUID, key: str,
    status_code: int, body: bytes, media_type: str | None,
) -> None:
    record = await session.scalar(
        select(IdempotencyKey).where(IdempotencyKey.user_id == user_id, IdempotencyKey.key == key)
    )
    if record is None:
        return  # the command did not commit anything: nothing to remember
    rows = (await session.execute(
        select(distinct(AuditEvent.project_id)).where(AuditEvent.xid == record.xid)
    )).scalars().all()
    await session.execute(
        update(IdempotencyKey)
        .where(IdempotencyKey.user_id == user_id, IdempotencyKey.key == key,
               IdempotencyKey.completed_at.is_(None))
        .values(
            completed_at=datetime.now(UTC), status_code=status_code,
            response_body=body.decode("utf-8", errors="replace"), media_type=media_type,
            project_ids=[str(p) for p in rows if p is not None],
            system=any(p is None for p in rows),
        )
    )
    await session.commit()


async def purge_expired(session: AsyncSession) -> int:
    """Delete keys older than KEY_TTL. Returns the number removed."""
    result = await session.execute(
        delete(IdempotencyKey).where(IdempotencyKey.created_at < datetime.now(UTC) - KEY_TTL)
    )
    await session.commit()
    return result.rowcount


async def _check_replay_access(session: AsyncSession, record: IdempotencyKey, user: User) -> None:
    if record.system and not user.is_superuser:
        raise HTTPException(status.HTTP_403_FORBIDDEN, {"code": "PERMISSION_DENIED"})
    for project_id in record.project_ids or []:
        await require_writer(session, uuid.UUID(project_id), user)
