"""External registry (ADR-024): providers, pinned revisions, events and snapshots.

Rules of contract v1.0:
- identity = provider + namespace + type + id; the locator is not identity;
- a revision is an opaque string; the same object and revision with other bytes is an
  integrity conflict; `latest`, branches and working folders are not pinned inputs;
- the current revision moves only by explicit supersession, provider confirmation or a
  snapshot; unknown order keeps it and marks pending_reconciliation; a late old revision
  never rolls it back;
- an event id is permanent: a repeat with the same content changes nothing, other content
  with the same id is a conflict; rights are checked on every repeat;
- a fact of a type the provider is not authoritative for is kept as an unverified message.
"""
import base64
import binascii
import hashlib
import json
import uuid
from collections.abc import Awaitable, Callable
from datetime import datetime

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.external import (
    CONTRACT_VERSION, ExternalEvent, ExternalIdentityAlias, ExternalObject, ExternalProvider,
    ExternalRevision, ExternalSnapshot,
)
from app.models.user import User
from app.schemas.external import (
    AliasCreate, FactImport, ObjectRef, ProviderCreate, ProviderUpdate, SnapshotImport,
)
from app.services import audit_service
from app.services.permissions import require_manager

# Mutable pointers are not pinned revisions.
_UNPINNED = {"latest", "head", "current", "main", "master", "trunk", "develop", "tip", "working", "worktree"}
_UNPINNED_PREFIXES = ("refs/heads/", "heads/", "branch:", "file:", "workdir:")


def _http(code: int, error: str, **extra) -> HTTPException:
    return HTTPException(code, {"code": error, **extra})


def canonical_json(data) -> bytes:
    return json.dumps(data, sort_keys=True, ensure_ascii=False, separators=(",", ":"), default=str).encode()


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def check_pinned(revision: str) -> str:
    value = revision.strip()
    low = value.lower()
    if not value or low in _UNPINNED or low.startswith(_UNPINNED_PREFIXES):
        raise _http(status.HTTP_422_UNPROCESSABLE_CONTENT, "REVISION_NOT_PINNED", revision=revision)
    return value


def identity(obj: ExternalObject) -> dict:
    return {"provider": obj.provider.key, "namespace": obj.namespace, "type": obj.type, "id": obj.ext_id}


def same_identity(claim, obj: ExternalObject) -> bool:
    return isinstance(claim, dict) and all(
        str(claim.get(k)) == v for k, v in identity(obj).items()
    )


def object_view(obj: ExternalObject) -> dict:
    return {
        "id": obj.id, "provider": obj.provider.key, "namespace": obj.namespace, "type": obj.type,
        "ext_id": obj.ext_id, "locator": obj.locator, "current_revision": obj.current_revision,
        "revision_state": obj.revision_state, "state_as_of": obj.state_as_of, "status": obj.status,
        "is_training": obj.provider.is_training,
    }


# ── Provider registry (superuser) ────────────────────────────────────────────

def require_superuser(user: User) -> None:
    if not user.is_superuser:
        raise _http(status.HTTP_403_FORBIDDEN, "PERMISSION_DENIED")


async def create_provider(session: AsyncSession, data: ProviderCreate, user: User) -> ExternalProvider:
    require_superuser(user)
    if await session.scalar(select(ExternalProvider.id).where(ExternalProvider.key == data.key)):
        raise _http(status.HTTP_409_CONFLICT, "PROVIDER_KEY_TAKEN")
    provider = ExternalProvider(**data.model_dump(), created_by=user.id)
    session.add(provider)
    await session.flush()
    await _audit(session, user, "external_provider", provider.id, "created", after=data.model_dump(mode="json"))
    await session.commit()
    return provider


async def update_provider(
    session: AsyncSession, provider_id: uuid.UUID, data: ProviderUpdate, user: User
) -> ExternalProvider:
    """The key and the training mark are permanent; namespaces, types and activity may change."""
    require_superuser(user)
    provider = await session.get(ExternalProvider, provider_id)
    if provider is None:
        raise _http(status.HTTP_404_NOT_FOUND, "PROVIDER_NOT_FOUND")
    fields = ("name", "acquisition", "namespaces", "fact_types", "active")
    before = audit_service.snapshot(provider, fields)
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(provider, key, value)
    await _audit(session, user, "external_provider", provider.id, "updated",
                 *audit_service.diff(before, audit_service.snapshot(provider, fields)))
    await session.commit()
    return provider


async def list_providers(session: AsyncSession) -> list[ExternalProvider]:
    return list((await session.scalars(select(ExternalProvider).order_by(ExternalProvider.key))).all())


async def get_provider(session: AsyncSession, key: str, *, for_import: bool = False) -> ExternalProvider:
    provider = await session.scalar(select(ExternalProvider).where(ExternalProvider.key == key))
    if provider is None:
        raise _http(status.HTTP_404_NOT_FOUND, "PROVIDER_NOT_FOUND", provider=key)
    if for_import and not provider.active:
        raise _http(status.HTTP_409_CONFLICT, "PROVIDER_INACTIVE", provider=key)
    return provider


# ── Objects ──────────────────────────────────────────────────────────────────

async def find_object(session: AsyncSession, ref: ObjectRef) -> ExternalObject | None:
    """Resolves identity, following an explicit alias of a former identity."""
    provider = await get_provider(session, ref.provider)
    obj = await session.scalar(select(ExternalObject).where(
        ExternalObject.provider_id == provider.id, ExternalObject.namespace == ref.namespace,
        ExternalObject.type == ref.type, ExternalObject.ext_id == ref.id,
    ))
    if obj is None:
        alias = await session.scalar(select(ExternalIdentityAlias).where(
            ExternalIdentityAlias.provider_id == provider.id, ExternalIdentityAlias.namespace == ref.namespace,
            ExternalIdentityAlias.type == ref.type, ExternalIdentityAlias.ext_id == ref.id,
        ))
        if alias is not None:
            obj = await session.get(ExternalObject, alias.object_id)
    return obj


async def require_object(session: AsyncSession, ref: ObjectRef) -> ExternalObject:
    obj = await find_object(session, ref)
    if obj is None:
        raise _http(status.HTTP_422_UNPROCESSABLE_CONTENT, "EXTERNAL_OBJECT_UNKNOWN", object=ref.model_dump())
    return obj


async def get_or_create_object(
    session: AsyncSession, provider: ExternalProvider, namespace: str, type_: str, ext_id: str,
    locator: str | None = None,
) -> ExternalObject:
    if namespace not in provider.namespaces:
        raise _http(status.HTTP_403_FORBIDDEN, "NAMESPACE_NOT_ALLOWED", provider=provider.key, namespace=namespace)
    obj = await find_object(session, ObjectRef(provider=provider.key, namespace=namespace, type=type_, id=ext_id))
    if obj is None:
        obj = ExternalObject(provider_id=provider.id, namespace=namespace, type=type_, ext_id=ext_id,
                             locator=locator, revision_state="unknown", status="active")
        session.add(obj)
        await session.flush()
        await session.refresh(obj, ["provider"])
    elif locator and obj.locator != locator:
        obj.locator = locator   # a new address never changes identity
    return obj


async def get_revision(session: AsyncSession, obj: ExternalObject, revision: str) -> ExternalRevision | None:
    return await session.scalar(select(ExternalRevision).where(
        ExternalRevision.object_id == obj.id, ExternalRevision.revision == revision,
    ))


async def object_detail(session: AsyncSession, ref: ObjectRef) -> dict:
    obj = await find_object(session, ref)
    if obj is None:
        raise _http(status.HTTP_404_NOT_FOUND, "EXTERNAL_OBJECT_NOT_FOUND")
    revisions = list((await session.scalars(
        select(ExternalRevision).where(ExternalRevision.object_id == obj.id).order_by(ExternalRevision.created_at)
    )).all())
    aliases = list((await session.scalars(
        select(ExternalIdentityAlias).where(ExternalIdentityAlias.object_id == obj.id)
    )).all())
    return {
        "object": object_view(obj), "revisions": revisions,
        "aliases": [{"provider": obj.provider.key, "namespace": a.namespace, "type": a.type, "id": a.ext_id}
                    for a in aliases],
    }


async def get_revision_by_id(session: AsyncSession, revision_id: uuid.UUID) -> ExternalRevision | None:
    return await session.get(ExternalRevision, revision_id)


# ── Revisions and ordering ───────────────────────────────────────────────────

def _decode(content: dict | None, content_base64: str | None, claims: dict | None) -> tuple[bytes | None, dict]:
    if content is not None:
        return canonical_json(content), content
    if content_base64 is not None:
        try:
            raw = base64.b64decode(content_base64, validate=True)
        except (binascii.Error, ValueError):
            raise _http(status.HTTP_422_UNPROCESSABLE_CONTENT, "CONTENT_INVALID")
        return raw, claims or {}
    return None, claims or {}


async def _is_ancestor(session: AsyncSession, obj: ExternalObject, older: str, newer: str) -> bool:
    """True if `newer` supersedes `older` through a chain of explicit supersessions."""
    seen: set[str] = set()
    cursor = newer
    while cursor and cursor not in seen:
        seen.add(cursor)
        row = await get_revision(session, obj, cursor)
        if row is None or row.supersedes is None:
            return False
        if row.supersedes == older:
            return True
        cursor = row.supersedes
    return False


async def register_revision(
    session: AsyncSession, provider: ExternalProvider, obj: ExternalObject, user: User, *,
    revision: str | None, raw: bytes | None, claims: dict, media_type: str | None, observed_at: datetime,
    asserted_by: str | None = None, provenance: dict | None = None, supersedes: str | None = None,
    confirmed: bool = False, revoked: bool = False,
) -> tuple[ExternalRevision, dict]:
    """Pins a revision and applies ordering. Returns the revision and the outcome."""
    digest = sha256(raw) if raw is not None else None
    if revision is None:
        if digest is None:
            raise _http(status.HTTP_422_UNPROCESSABLE_CONTENT, "REVISION_REQUIRED")
        revision = f"sha256:{digest}"
    revision = check_pinned(revision)
    if supersedes is not None:
        supersedes = check_pinned(supersedes)
        if supersedes == revision:
            raise _http(status.HTTP_422_UNPROCESSABLE_CONTENT, "SUPERSEDES_ITSELF")

    row = await get_revision(session, obj, revision)
    created = row is None
    if row is not None:
        if digest is not None and row.sha256 is not None and row.sha256 != digest:
            raise _http(status.HTTP_409_CONFLICT, "INTEGRITY_CONFLICT", object=identity(obj), revision=revision,
                        pinned_sha256=row.sha256, received_sha256=digest)
        if row.sha256 is None and raw is not None:   # a reference known from a snapshot gets its original
            row.content, row.sha256, row.media_type, row.claims = raw, digest, media_type, claims
        if supersedes is not None and row.supersedes is None:
            row.supersedes = supersedes
    else:
        row = ExternalRevision(
            object_id=obj.id, revision=revision, content=raw, sha256=digest, media_type=media_type,
            claims=claims, observed_at=observed_at, asserted_by=asserted_by, registered_by=user.id,
            provenance=provenance or {}, supersedes=supersedes, is_revocation=revoked,
            verified=obj.type in provider.fact_types,
        )
        session.add(row)
        await session.flush()
    if supersedes is not None:
        older = await get_revision(session, obj, supersedes)
        if older is not None and older.superseded_by is None:
            older.superseded_by = revision

    outcome = {"revision": revision, "created": created, "verified": row.verified}
    if not row.verified:
        outcome["effect"] = "unverified_message"   # stored, never moves the current revision
    else:
        outcome["effect"] = await _apply_order(session, obj, row, confirmed=confirmed, observed_at=observed_at, user=user)
    outcome["current_revision"] = obj.current_revision
    outcome["revision_state"] = obj.revision_state
    if created:
        await _audit(session, user, "external_revision", row.id, "registered",
                     after={"object": identity(obj), "revision": revision, "sha256": digest,
                            "verified": row.verified, "effect": outcome["effect"]})
    return row, outcome


async def _apply_order(
    session: AsyncSession, obj: ExternalObject, row: ExternalRevision, *, confirmed: bool,
    observed_at: datetime, user: User,
) -> str:
    current = obj.current_revision
    if current == row.revision:
        if confirmed and (obj.state_as_of is None or observed_at >= obj.state_as_of):
            obj.revision_state, obj.state_as_of = "current", observed_at
            return "confirmed"
        return "unchanged"
    if current is not None and await _is_ancestor(session, obj, row.revision, current):
        return "stale"   # a late old revision does not roll the current one back
    if confirmed:
        if obj.state_as_of is not None and observed_at < obj.state_as_of:
            return "stale"
        await _set_current(session, obj, row, "current", observed_at, user)
        return "current_changed"
    if current is None:
        await _set_current(session, obj, row, "unconfirmed", observed_at, user)
        return "current_changed"
    if row.supersedes == current:
        await _set_current(session, obj, row, "current", observed_at, user)
        return "current_changed"
    obj.revision_state = "pending_reconciliation"
    return "pending_reconciliation"


async def _set_current(
    session: AsyncSession, obj: ExternalObject, row: ExternalRevision, state: str, as_of: datetime, user: User,
) -> None:
    from app.services import portfolio_service

    previous = obj.current_revision
    obj.current_revision, obj.revision_state, obj.state_as_of = row.revision, state, as_of
    obj.status = "revoked" if row.is_revocation else "active"
    if previous is not None and previous != row.revision:
        await portfolio_service.on_current_changed(session, obj, row.revision, user)


# ── Import operations ────────────────────────────────────────────────────────

async def require_import_rights(session: AsyncSession, project_id: uuid.UUID | None, user: User) -> None:
    """Superuser, or a manager of the given project. Registering a fact never grants the
    authority the fact speaks for — that comes from the provider's registration."""
    if user.is_superuser:
        return
    if project_id is None:
        raise _http(status.HTTP_403_FORBIDDEN, "PERMISSION_DENIED")
    await require_manager(session, project_id, user)


async def run_event(
    session: AsyncSession, provider: ExternalProvider, user: User, *, event_id: str | None,
    contract_version: str, kind: str, payload: dict, apply: Callable[[], Awaitable[tuple[dict, uuid.UUID | None, str | None]]],
    occurred_at: datetime | None = None, provenance: dict | None = None,
) -> tuple[dict, bool]:
    """Runs `apply` once per (provider, event_id). Returns (outcome, replayed)."""
    if contract_version != CONTRACT_VERSION:
        raise _http(status.HTTP_422_UNPROCESSABLE_CONTENT, "CONTRACT_VERSION_UNSUPPORTED",
                    supported=CONTRACT_VERSION)
    if event_id is None:
        outcome, _, _ = await apply()
        return outcome, False
    digest = sha256(canonical_json(payload))
    existing = await session.scalar(select(ExternalEvent).where(
        ExternalEvent.provider_id == provider.id, ExternalEvent.event_id == event_id,
    ).with_for_update())
    if existing is not None:
        if existing.content_sha256 != digest:
            raise _http(status.HTTP_409_CONFLICT, "EVENT_CONFLICT", event_id=event_id)
        return existing.outcome, True
    outcome, object_id, revision = await apply()
    session.add(ExternalEvent(
        provider_id=provider.id, event_id=event_id, contract_version=contract_version, kind=kind,
        object_id=object_id, revision=revision, occurred_at=occurred_at, content_sha256=digest,
        provenance=provenance or {}, outcome=json.loads(canonical_json(outcome)), registered_by=user.id,
    ))
    try:
        await session.flush()
    except IntegrityError:   # a concurrent delivery of the same event won the race
        await session.rollback()
        raise _http(status.HTTP_409_CONFLICT, "EVENT_IN_PROGRESS", event_id=event_id)
    return outcome, False


async def import_fact(session: AsyncSession, data: FactImport, user: User) -> dict:
    await require_import_rights(session, data.project_id, user)
    provider = await get_provider(session, data.provider, for_import=True)
    raw, claims = _decode(data.content, data.content_base64, data.claims)
    holder: dict = {}

    async def apply():
        obj = await get_or_create_object(session, provider, data.namespace, data.type, data.id, data.locator)
        row, outcome = await register_revision(
            session, provider, obj, user, revision=data.revision, raw=raw, claims=claims,
            media_type=data.media_type or ("application/json" if data.content is not None else None),
            observed_at=data.observed_at, asserted_by=data.asserted_by, provenance=data.provenance,
            supersedes=data.supersedes, confirmed=data.confirmed_current, revoked=data.revoked,
        )
        holder.update(obj=obj, row=row)
        return outcome, obj.id, row.revision

    outcome, replayed = await run_event(
        session, provider, user, event_id=data.event_id, contract_version=data.contract_version,
        kind="revision", payload=data.model_dump(mode="json", exclude={"project_id"}), apply=apply,
        occurred_at=data.observed_at, provenance=data.provenance,
    )
    if replayed:
        obj = await require_object(session, data)
        row = await get_revision(session, obj, outcome["revision"])
    else:
        obj, row = holder["obj"], holder["row"]
    await session.commit()
    await session.refresh(obj)
    return {"object": object_view(obj), "revision": row, "replayed": replayed, "outcome": outcome}


async def import_snapshot(session: AsyncSession, data: SnapshotImport, user: User) -> dict:
    """An authoritative export: listed revisions become current as of `as_of` (never older
    confirmed state); an object missing from the export is not deleted."""
    await require_import_rights(session, data.project_id, user)
    provider = await get_provider(session, data.provider, for_import=True)
    if data.namespace not in provider.namespaces:
        raise _http(status.HTTP_403_FORBIDDEN, "NAMESPACE_NOT_ALLOWED", provider=provider.key, namespace=data.namespace)
    holder: dict = {}

    async def apply():
        results: list[dict] = []
        seen: set[uuid.UUID] = set()
        for item in data.items:
            if item.type not in data.types:
                raise _http(status.HTTP_422_UNPROCESSABLE_CONTENT, "SNAPSHOT_ITEM_OUT_OF_SCOPE", type=item.type)
            raw, claims = _decode(item.content, item.content_base64, item.claims)
            obj = await get_or_create_object(session, provider, data.namespace, item.type, item.id, item.locator)
            _, outcome = await register_revision(
                session, provider, obj, user, revision=item.revision, raw=raw, claims=claims,
                media_type=item.media_type or ("application/json" if item.content is not None else None),
                observed_at=data.as_of, provenance={"snapshot": True, "cursor": data.cursor},
                confirmed=True, revoked=item.revoked,
            )
            seen.add(obj.id)
            results.append({"type": item.type, "id": item.id, **outcome})
        absent: list[str] = []
        if data.completeness == "full":
            rows = await session.scalars(select(ExternalObject).where(
                ExternalObject.provider_id == provider.id, ExternalObject.namespace == data.namespace,
                ExternalObject.type.in_(data.types),
            ))
            absent = [f"{o.type}/{o.ext_id}" for o in rows if o.id not in seen]
        result = {"items": results, "absent_not_deleted": absent}
        snapshot = ExternalSnapshot(
            provider_id=provider.id, namespace=data.namespace, types=list(data.types),
            completeness=data.completeness, as_of=data.as_of, cursor=data.cursor,
            items_count=len(data.items), result=json.loads(canonical_json(result)), registered_by=user.id,
        )
        session.add(snapshot)
        await session.flush()
        holder["snapshot"] = snapshot
        await _audit(session, user, "external_snapshot", snapshot.id, "imported",
                     after={"provider": provider.key, "namespace": data.namespace,
                            "completeness": data.completeness, "items": len(data.items)})
        return {"snapshot_id": str(snapshot.id), **result}, None, None

    outcome, replayed = await run_event(
        session, provider, user, event_id=data.event_id, contract_version=data.contract_version,
        kind="snapshot", payload=data.model_dump(mode="json", exclude={"project_id"}), apply=apply,
        occurred_at=data.as_of,
    )
    snapshot = holder.get("snapshot") or await session.get(ExternalSnapshot, uuid.UUID(outcome["snapshot_id"]))
    await session.commit()
    return {**{c: getattr(snapshot, c) for c in (
        "id", "namespace", "types", "completeness", "as_of", "cursor", "items_count", "result", "created_at",
    )}, "replayed": replayed}


async def create_alias(session: AsyncSession, data: AliasCreate, user: User) -> dict:
    """Identity change with history: the former identity keeps resolving to the object."""
    require_superuser(user)
    if data.old.provider != data.current.provider:
        raise _http(status.HTTP_422_UNPROCESSABLE_CONTENT, "ALIAS_ACROSS_PROVIDERS")
    obj = await require_object(session, data.current)
    provider = await get_provider(session, data.old.provider)
    taken = await session.scalar(select(ExternalObject.id).where(
        ExternalObject.provider_id == provider.id, ExternalObject.namespace == data.old.namespace,
        ExternalObject.type == data.old.type, ExternalObject.ext_id == data.old.id,
    ))
    if taken is not None or await find_object(session, data.old) is not None:
        raise _http(status.HTTP_409_CONFLICT, "IDENTITY_TAKEN")
    alias = ExternalIdentityAlias(provider_id=provider.id, namespace=data.old.namespace, type=data.old.type,
                                  ext_id=data.old.id, object_id=obj.id, reason=data.reason, created_by=user.id)
    session.add(alias)
    await session.flush()
    await _audit(session, user, "external_alias", alias.id, "created",
                 after={"old": data.old.model_dump(), "current": data.current.model_dump(), "reason": data.reason})
    await session.commit()
    return await object_detail(session, data.current)


async def list_events(session: AsyncSession, provider_key: str, user: User, limit: int = 100) -> list[ExternalEvent]:
    require_superuser(user)
    provider = await get_provider(session, provider_key)
    return list((await session.scalars(
        select(ExternalEvent).where(ExternalEvent.provider_id == provider.id)
        .order_by(ExternalEvent.created_at.desc()).limit(limit)
    )).all())


async def _audit(
    session: AsyncSession, user: User, entity_type: str, entity_id: uuid.UUID, action: str,
    before: dict | None = None, after: dict | None = None,
) -> None:
    await audit_service.record(
        session, actor_id=user.id, project_id=None, task_id=None,
        entity_type=entity_type, entity_id=entity_id, action=action, before=before, after=after,
    )
