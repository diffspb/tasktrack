"""Служебные учётные записи и ключи API (FR-003, TT-05, ADR-017).

- ключ выдаётся только служебной учётной записи, токен показывается один раз;
- REST и MCP принимают один и тот же токен и одинаково его проверяют;
- отзыв, истечение, ротация и деактивация действуют сразу, без перезапуска;
- права служебной учётной записи — через членство в проекте, как у людей;
- в рабочей установке запрещены AUTH_STUB и MCP без ключа; ключи не пишутся в лог.
"""
import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from mcp.shared.exceptions import McpError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_session
from app.core.config import Settings, settings
from app.main import app
from app.models.api_key import ApiKey
from app.models.project import ProjectMember, ProjectMemberRole
from app.models.user import User
from app.schemas.project import ProjectCreate
from app.schemas.task import TaskCreate
from app.services import project_service, task_service


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture
async def superuser(db_session: AsyncSession) -> User:
    u = User(
        id=uuid.uuid4(), email=f"root_{uuid.uuid4().hex[:6]}@t.com", display_name="Root",
        keycloak_id=str(uuid.uuid4()), is_active=True, is_superuser=True,
    )
    db_session.add(u)
    await db_session.flush()
    return u


@pytest_asyncio.fixture
async def admin_client(client: AsyncClient, superuser: User) -> AsyncClient:
    app.dependency_overrides[get_current_user] = lambda: superuser
    return client


@pytest_asyncio.fixture
async def token_client(db_session: AsyncSession, monkeypatch) -> AsyncClient:
    """Real authentication (no get_current_user override), stub auth disabled."""
    monkeypatch.setattr(settings, "auth_stub", False)

    async def override_get_session():
        yield db_session

    app.dependency_overrides[get_session] = override_get_session

    # admin_client overrides get_current_user on the same app: lift that override
    # for the duration of each token_client request so the real auth path runs.
    saved: dict = {}

    async def lift_override(request):
        saved["user"] = app.dependency_overrides.pop(get_current_user, None)

    async def restore_override(response):
        if saved.get("user") is not None:
            app.dependency_overrides[get_current_user] = saved["user"]

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test",
        event_hooks={"request": [lift_override], "response": [restore_override]},
    ) as ac:
        yield ac
    app.dependency_overrides.clear()


async def _service_account_with_key(admin_client: AsyncClient, **key_fields) -> dict:
    r = await admin_client.post("/api/v1/admin/service-accounts", json={
        "email": f"agent_{uuid.uuid4().hex[:6]}@agents", "display_name": "Agent",
    })
    assert r.status_code == 201, r.text
    account = r.json()
    r = await admin_client.post(
        f"/api/v1/admin/service-accounts/{account['id']}/api-keys",
        json={"name": "ci", **key_fields},
    )
    assert r.status_code == 201, r.text
    return {"account": account, "key": r.json()}


# ── Управление: только суперпользователь ─────────────────────────────────────

async def test_admin_endpoints_require_superuser(client: AsyncClient):
    r = await client.post("/api/v1/admin/service-accounts", json={
        "email": "x@agents", "display_name": "X",
    })
    assert r.status_code == 403


async def test_key_only_for_service_accounts(admin_client: AsyncClient, stub_user: User):
    r = await admin_client.post(
        f"/api/v1/admin/service-accounts/{stub_user.id}/api-keys", json={"name": "k"}
    )
    assert r.status_code == 400
    assert r.json()["detail"]["code"] == "NOT_SERVICE_ACCOUNT"


async def test_token_shown_once_and_not_stored(admin_client: AsyncClient, db_session: AsyncSession):
    ctx = await _service_account_with_key(admin_client)
    token = ctx["key"]["token"]
    assert token.startswith("tt_") and len(token) > 40

    r = await admin_client.get(f"/api/v1/admin/service-accounts/{ctx['account']['id']}/api-keys")
    listed = r.json()
    assert len(listed) == 1
    assert "token" not in listed[0] and "key_hash" not in listed[0]
    assert token.startswith(listed[0]["prefix"])

    stored = await db_session.get(ApiKey, uuid.UUID(ctx["key"]["id"]))
    assert token not in stored.key_hash


# ── Аутентификация REST ──────────────────────────────────────────────────────

async def test_rest_authenticates_by_key(
    admin_client: AsyncClient, token_client: AsyncClient, db_session: AsyncSession
):
    ctx = await _service_account_with_key(admin_client)
    r = await token_client.get("/api/v1/users/me", headers=_auth(ctx["key"]["token"]))
    assert r.status_code == 200
    assert r.json()["email"] == ctx["account"]["email"]

    stored = await db_session.get(ApiKey, uuid.UUID(ctx["key"]["id"]))
    assert stored.last_used_at is not None


async def test_unknown_key_rejected(token_client: AsyncClient):
    r = await token_client.get("/api/v1/users/me", headers=_auth("tt_" + "x" * 43))
    assert r.status_code == 401


async def test_revoked_key_rejected_immediately(
    admin_client: AsyncClient, token_client: AsyncClient
):
    ctx = await _service_account_with_key(admin_client)
    token = ctx["key"]["token"]
    assert (await token_client.get("/api/v1/users/me", headers=_auth(token))).status_code == 200

    r = await admin_client.delete(f"/api/v1/admin/api-keys/{ctx['key']['id']}")
    assert r.status_code == 204
    assert (await token_client.get("/api/v1/users/me", headers=_auth(token))).status_code == 401


async def test_expired_key_rejected(admin_client: AsyncClient, token_client: AsyncClient):
    past = (datetime.now(UTC) - timedelta(minutes=1)).isoformat()
    ctx = await _service_account_with_key(admin_client, expires_at=past)
    r = await token_client.get("/api/v1/users/me", headers=_auth(ctx["key"]["token"]))
    assert r.status_code == 401


async def test_rotate_replaces_key(admin_client: AsyncClient, token_client: AsyncClient):
    ctx = await _service_account_with_key(admin_client)
    old = ctx["key"]["token"]

    r = await admin_client.post(f"/api/v1/admin/api-keys/{ctx['key']['id']}/rotate")
    assert r.status_code == 201
    new = r.json()["token"]
    assert new != old and r.json()["name"] == "ci"

    assert (await token_client.get("/api/v1/users/me", headers=_auth(old))).status_code == 401
    assert (await token_client.get("/api/v1/users/me", headers=_auth(new))).status_code == 200


async def test_deactivated_account_rejected(admin_client: AsyncClient, token_client: AsyncClient):
    ctx = await _service_account_with_key(admin_client)
    r = await admin_client.patch(
        f"/api/v1/admin/service-accounts/{ctx['account']['id']}", json={"is_active": False}
    )
    assert r.status_code == 200 and r.json()["is_active"] is False
    r = await token_client.get("/api/v1/users/me", headers=_auth(ctx["key"]["token"]))
    assert r.status_code == 401


async def test_service_account_rights_follow_membership(
    admin_client: AsyncClient, token_client: AsyncClient,
    db_session: AsyncSession, stub_user: User,
):
    """Ключ не даёт прав сверх роли: viewer читает, но не меняет."""
    ctx = await _service_account_with_key(admin_client)
    project = await project_service.create_project(
        db_session, ProjectCreate(name="SA", key=uuid.uuid4().hex[:8].upper()), stub_user
    )
    task = await task_service.create_task(db_session, project.id, TaskCreate(title="T"), stub_user)
    db_session.add(ProjectMember(
        project_id=project.id, user_id=uuid.UUID(ctx["account"]["id"]), role=ProjectMemberRole.viewer,
    ))
    await db_session.flush()
    headers = _auth(ctx["key"]["token"])

    assert (await token_client.get(f"/api/v1/tasks/{task.id}", headers=headers)).status_code == 200
    r = await token_client.patch(
        f"/api/v1/tasks/{task.id}", json={"title": "X", "version": 1}, headers=headers
    )
    assert r.status_code == 403


# ── MCP: тот же токен, та же проверка ────────────────────────────────────────

class _TestSessionFactory:
    """Stands in for SessionLocal: yields the savepoint-isolated test session."""
    def __init__(self, session: AsyncSession):
        self._session = session

    def __call__(self):
        return self

    async def __aenter__(self):
        return self._session

    async def __aexit__(self, *args):
        pass


def _mcp_ctx(token: str | None):
    ctx = MagicMock()
    ctx.request_context.request.headers = {"authorization": f"Bearer {token}"} if token else {}
    return ctx


async def test_mcp_authenticates_by_same_key(admin_client: AsyncClient, db_session: AsyncSession):
    from app.mcp.utils import McpSession

    ctx = await _service_account_with_key(admin_client)
    with patch("app.mcp.utils.SessionLocal", _TestSessionFactory(db_session)):
        async with McpSession(_mcp_ctx(ctx["key"]["token"])) as (_, user):
            assert str(user.id) == ctx["account"]["id"]

        await admin_client.delete(f"/api/v1/admin/api-keys/{ctx['key']['id']}")
        with pytest.raises(McpError):
            async with McpSession(_mcp_ctx(ctx["key"]["token"])):
                pass


async def test_legacy_mcp_agents_do_not_log_keys(
    db_session: AsyncSession, stub_user: User, monkeypatch, capsys
):
    from app.mcp import auth as mcp_auth

    monkeypatch.setattr(settings, "mcp_agents", f"very-secret-key-123:{stub_user.id}")
    monkeypatch.setattr(mcp_auth, "_agents", {})
    with patch("app.mcp.auth.SessionLocal", _TestSessionFactory(db_session)):
        await mcp_auth.resolve_all_agents()
    out = capsys.readouterr().out
    assert "very-secret-key-123" not in out
    assert stub_user.email in out


# ── Защита рабочей установки ─────────────────────────────────────────────────

def test_production_refuses_auth_stub():
    from app.core.config import validate_runtime

    with pytest.raises(RuntimeError, match="AUTH_STUB"):
        validate_runtime(Settings(_env_file=None, app_env="production", auth_stub=True))


def test_production_refuses_keyless_mcp():
    from app.core.config import validate_runtime

    with pytest.raises(RuntimeError, match="MCP_AGENT_USER_ID"):
        validate_runtime(Settings(_env_file=None, app_env="production", mcp_agent_user_id=uuid.uuid4()))


def test_dev_allows_stub_and_production_allows_keys():
    from app.core.config import validate_runtime

    validate_runtime(Settings(_env_file=None, app_env="dev", auth_stub=True, mcp_agent_user_id=uuid.uuid4()))
    validate_runtime(Settings(_env_file=None, app_env="production"))


# ── CLI на сервере ───────────────────────────────────────────────────────────

async def test_cli_issues_and_revokes_key(make_database, alembic):
    import asyncio
    import os
    import sys
    from pathlib import Path

    url = await make_database()
    await alembic(url, "upgrade", "head")
    backend = Path(__file__).parent.parent

    async def cli(*args: str) -> str:
        proc = await asyncio.create_subprocess_exec(
            sys.executable, "scripts/service_account.py", *args,
            cwd=backend, env={**os.environ, "DATABASE_URL": url, "PYTHONPATH": str(backend)},
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT,
        )
        out, _ = await asyncio.wait_for(proc.communicate(), timeout=60)
        assert proc.returncode == 0, out.decode()
        return out.decode()

    await cli("create", "--email", "cli@agents", "--name", "CLI agent")
    out = await cli("issue", "--email", "cli@agents", "--key-name", "laptop", "--expires-days", "30")
    token = out.strip().splitlines()[-1]
    key_id = out.split("key id=")[1].split()[0]
    assert token.startswith("tt_")

    listed = await cli("keys", "--email", "cli@agents")
    assert token not in listed and "active" in listed

    await cli("revoke", "--key-id", key_id)
    assert "revoked" in await cli("keys", "--email", "cli@agents")
