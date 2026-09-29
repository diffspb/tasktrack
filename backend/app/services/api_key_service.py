"""Service accounts and their API keys (ADR-017, FR-003 TT-05).

Permission checks (superuser) live in the API layer so that the CLI
(scripts/service_account.py), which runs with shell access to the server,
can reuse these functions.
"""
import hashlib
import secrets
import uuid
from datetime import UTC, datetime, timedelta

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.api_key import ApiKey
from app.models.user import User
from app.services import audit_service

TOKEN_PREFIX = "tt_"
_DISPLAY_PREFIX_LEN = 10  # "tt_" + 7 characters of the secret
# last_used_at is informational; don't write on every request.
_LAST_USED_RESOLUTION = timedelta(minutes=1)


def is_api_token(token: str | None) -> bool:
    return bool(token) and token.startswith(TOKEN_PREFIX)


def hash_token(token: str) -> str:
    # Tokens are 256-bit random values: a fast hash is enough, no salt/KDF needed.
    return hashlib.sha256(token.encode()).hexdigest()


async def create_service_account(
    session: AsyncSession, email: str, display_name: str, *, actor_id: uuid.UUID | None = None
) -> User:
    if await session.scalar(select(User).where(User.email == email)):
        raise HTTPException(status.HTTP_409_CONFLICT, {"code": "EMAIL_TAKEN"})
    user_id = uuid.uuid4()
    user = User(
        id=user_id, email=email, display_name=display_name,
        # keycloak_id is required and unique; this value can never match a Keycloak sub.
        keycloak_id=f"service:{user_id}",
        is_active=True, is_service=True,
    )
    session.add(user)
    await _audit(session, actor_id, "service_account", user.id, "created",
                 after={"email": email, "display_name": display_name})
    await session.commit()
    return user


async def list_service_accounts(session: AsyncSession) -> list[User]:
    return list((await session.scalars(
        select(User).where(User.is_service.is_(True)).order_by(User.created_at)
    )).all())


async def get_service_account(session: AsyncSession, user_id: uuid.UUID) -> User:
    user = await session.get(User, user_id)
    if not user:
        raise HTTPException(status.HTTP_404_NOT_FOUND, {"code": "USER_NOT_FOUND"})
    if not user.is_service:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, {"code": "NOT_SERVICE_ACCOUNT"})
    return user


async def set_service_account_active(
    session: AsyncSession, user_id: uuid.UUID, is_active: bool, *, actor_id: uuid.UUID | None = None
) -> User:
    user = await get_service_account(session, user_id)
    if user.is_active != is_active:
        await _audit(session, actor_id, "service_account", user.id, "updated",
                     before={"is_active": user.is_active}, after={"is_active": is_active})
    user.is_active = is_active
    await session.commit()
    return user


async def issue_key(
    session: AsyncSession,
    user_id: uuid.UUID,
    name: str,
    *,
    expires_at: datetime | None = None,
    created_by: uuid.UUID | None = None,
) -> tuple[ApiKey, str]:
    """Returns the stored key and the plaintext token. The token is not retrievable later."""
    await get_service_account(session, user_id)
    key, token = _new_key(user_id, name, expires_at, created_by)
    session.add(key)
    await session.flush()
    await _audit(session, created_by, "api_key", key.id, "created", after=_key_snapshot(key))
    await session.commit()
    return key, token


async def list_keys(session: AsyncSession, user_id: uuid.UUID) -> list[ApiKey]:
    await get_service_account(session, user_id)
    return list((await session.scalars(
        select(ApiKey).where(ApiKey.user_id == user_id).order_by(ApiKey.created_at)
    )).all())


async def revoke_key(
    session: AsyncSession, key_id: uuid.UUID, *, actor_id: uuid.UUID | None = None
) -> ApiKey:
    key = await _get_key(session, key_id)
    if key.revoked_at is None:
        key.revoked_at = datetime.now(UTC)
        await _audit(session, actor_id, "api_key", key.id, "revoked", before=_key_snapshot(key))
        await session.commit()
    return key


async def rotate_key(
    session: AsyncSession, key_id: uuid.UUID, *, created_by: uuid.UUID | None = None
) -> tuple[ApiKey, str]:
    """Revoke the key and issue a replacement with the same name and expiry, atomically."""
    old = await _get_key(session, key_id, for_update=True)
    if old.revoked_at is not None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, {"code": "API_KEY_REVOKED"})
    old.revoked_at = datetime.now(UTC)
    new, token = _new_key(old.user_id, old.name, old.expires_at, created_by)
    session.add(new)
    await session.flush()
    await _audit(session, created_by, "api_key", old.id, "revoked",
                 before=_key_snapshot(old), after={"replaced_by": str(new.id)})
    await _audit(session, created_by, "api_key", new.id, "created", after=_key_snapshot(new))
    await session.commit()
    return new, token


async def authenticate(session: AsyncSession, token: str) -> User | None:
    """User for a valid token, else None. Checked against the DB on every call,
    so revocation, expiry and deactivation take effect immediately."""
    key = await session.scalar(select(ApiKey).where(ApiKey.key_hash == hash_token(token)))
    now = datetime.now(UTC)
    if key is None or key.revoked_at is not None:
        return None
    if key.expires_at is not None and key.expires_at <= now:
        return None
    user = await session.get(User, key.user_id)
    if user is None or not user.is_active or not user.is_service:
        return None
    if key.last_used_at is None or now - key.last_used_at > _LAST_USED_RESOLUTION:
        key.last_used_at = now
        await session.commit()
    return user


def _key_snapshot(key: ApiKey) -> dict:
    # The token is never stored; the hash is not logged either.
    return audit_service.snapshot(key, ("user_id", "name", "prefix", "expires_at"))


async def _audit(
    session: AsyncSession, actor_id: uuid.UUID | None, entity_type: str,
    entity_id: uuid.UUID, action: str, before: dict | None = None, after: dict | None = None,
) -> None:
    await audit_service.record(
        session, actor_id=actor_id, project_id=None,
        entity_type=entity_type, entity_id=entity_id, action=action, before=before, after=after,
    )


def _new_key(
    user_id: uuid.UUID, name: str, expires_at: datetime | None, created_by: uuid.UUID | None
) -> tuple[ApiKey, str]:
    token = TOKEN_PREFIX + secrets.token_urlsafe(32)
    key = ApiKey(
        user_id=user_id, name=name, prefix=token[:_DISPLAY_PREFIX_LEN],
        key_hash=hash_token(token), expires_at=expires_at, created_by=created_by,
    )
    return key, token


async def _get_key(session: AsyncSession, key_id: uuid.UUID, *, for_update: bool = False) -> ApiKey:
    stmt = select(ApiKey).where(ApiKey.id == key_id)
    if for_update:
        stmt = stmt.with_for_update()
    key = await session.scalar(stmt)
    if not key:
        raise HTTPException(status.HTTP_404_NOT_FOUND, {"code": "API_KEY_NOT_FOUND"})
    return key
