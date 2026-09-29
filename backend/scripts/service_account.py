"""Service accounts and API keys from the server shell (ADR-017, FR-003 TT-05).

Inside the container:
  docker compose ... exec app python scripts/service_account.py <command> ...

Commands:
  create     --email E --name N             create a service account
  list                                      list service accounts
  issue      --email E --key-name K [--expires-days D]
                                            issue a key; the token is printed once
  keys       --email E                      list keys (never the tokens)
  revoke     --key-id ID                    revoke a key immediately
  rotate     --key-id ID                    revoke and issue a replacement
  deactivate --email E / activate --email E

Access to projects is granted as for people: add the account as a project member
(viewer = read-only agent). The key is sent as `Authorization: Bearer <token>`
to both REST (/api/v1) and MCP (/mcp/sse).
"""
import argparse
import asyncio
import uuid
from datetime import UTC, datetime, timedelta

from fastapi import HTTPException
from sqlalchemy import select

from app.core.db import SessionLocal
from app.models.user import User
from app.services import api_key_service as svc


async def _account_id(session, email: str) -> uuid.UUID:
    user = await session.scalar(select(User).where(User.email == email))
    if user is None:
        raise SystemExit(f"no user with email {email}")
    return user.id


def _fmt(dt: datetime | None) -> str:
    return dt.strftime("%Y-%m-%d %H:%M") if dt else "-"


async def run(args: argparse.Namespace) -> None:
    async with SessionLocal() as session:
        if args.cmd == "create":
            user = await svc.create_service_account(session, args.email, args.name)
            print(f"created {user.email} id={user.id}")
        elif args.cmd == "list":
            for u in await svc.list_service_accounts(session):
                print(f"{u.id}  {u.email:40}  {'active' if u.is_active else 'inactive'}")
        elif args.cmd == "issue":
            expires = (
                datetime.now(UTC) + timedelta(days=args.expires_days) if args.expires_days else None
            )
            key, token = await svc.issue_key(
                session, await _account_id(session, args.email), args.key_name, expires_at=expires
            )
            print(f"key id={key.id} name={key.name} expires={_fmt(key.expires_at)}")
            print("token (shown once, store it now):")
            print(token)
        elif args.cmd == "keys":
            for k in await svc.list_keys(session, await _account_id(session, args.email)):
                state = "revoked" if k.revoked_at else "active"
                print(f"{k.id}  {k.prefix}…  {k.name:20}  {state:8}  "
                      f"expires={_fmt(k.expires_at)}  last_used={_fmt(k.last_used_at)}")
        elif args.cmd == "revoke":
            await svc.revoke_key(session, uuid.UUID(args.key_id))
            print(f"revoked {args.key_id}")
        elif args.cmd == "rotate":
            key, token = await svc.rotate_key(session, uuid.UUID(args.key_id))
            print(f"revoked {args.key_id}; new key id={key.id}")
            print("token (shown once, store it now):")
            print(token)
        elif args.cmd in ("activate", "deactivate"):
            user = await svc.set_service_account_active(
                session, await _account_id(session, args.email), args.cmd == "activate"
            )
            print(f"{user.email}: {'active' if user.is_active else 'inactive'}")


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("create"); c.add_argument("--email", required=True); c.add_argument("--name", required=True)
    sub.add_parser("list")
    i = sub.add_parser("issue")
    i.add_argument("--email", required=True); i.add_argument("--key-name", required=True)
    i.add_argument("--expires-days", type=int)
    k = sub.add_parser("keys"); k.add_argument("--email", required=True)
    for name in ("revoke", "rotate"):
        sub.add_parser(name).add_argument("--key-id", required=True)
    for name in ("activate", "deactivate"):
        sub.add_parser(name).add_argument("--email", required=True)
    try:
        asyncio.run(run(p.parse_args()))
    except HTTPException as e:
        raise SystemExit(f"error: {e.detail}")


if __name__ == "__main__":
    main()
