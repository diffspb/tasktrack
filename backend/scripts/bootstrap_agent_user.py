"""
Create (or reuse) an MCP agent user and add it to all existing projects.

Usage:
    cd backend
    python scripts/bootstrap_agent_user.py                          # email=agent@tasktrack
    python scripts/bootstrap_agent_user.py --email pm@tasktrack     # named agent
    python scripts/bootstrap_agent_user.py --email exec@tasktrack

Output:
    MCP_AGENT_USER_ID=<uuid>    (for single-agent / dev mode)
    MCP_AGENTS+=<key>:<uuid>    (for multi-agent prod mode — choose a key yourself)
"""

import asyncio
import sys
import os
import argparse

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from sqlalchemy import select

from app.core.db import SessionLocal
from app.models.project import Project, ProjectMember, ProjectMemberRole
from app.models.user import User


async def main(email: str) -> None:
    async with SessionLocal() as session:
        user = await session.scalar(select(User).where(User.email == email))
        if user is None:
            keycloak_id = f"agent-mcp-{email.split('@')[0]}"
            display_name = f"MCP Agent ({email.split('@')[0]})"
            user = User(
                email=email,
                display_name=display_name,
                keycloak_id=keycloak_id,
                is_active=True,
            )
            session.add(user)
            await session.flush()
            print(f"Created agent user: {user.id} ({email})")
        else:
            print(f"Agent user already exists: {user.id} ({email})")

        projects = list((await session.scalars(
            select(Project).where(
                Project.is_archived.is_(False),
                Project.deleted_at.is_(None),
            )
        )).all())

        added = 0
        for project in projects:
            existing = await session.scalar(
                select(ProjectMember).where(
                    ProjectMember.project_id == project.id,
                    ProjectMember.user_id == user.id,
                )
            )
            if existing is None:
                session.add(ProjectMember(
                    project_id=project.id,
                    user_id=user.id,
                    role=ProjectMemberRole.member,
                ))
                added += 1

        await session.commit()

    print(f"Added to {added} project(s).")
    print()
    print("── Single-agent / dev mode (no key required) ──")
    print(f"  MCP_AGENT_USER_ID={user.id}")
    print()
    print("── Multi-agent mode (choose your own key) ──")
    print(f"  Add to MCP_AGENTS:  <your-secret-key>:{user.id}")
    print("  Example: MCP_AGENTS=my-key-abc123:{uuid1},another-key:{uuid2}".replace("{uuid1}", str(user.id)))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Bootstrap an MCP agent user")
    parser.add_argument("--email", default="agent@tasktrack", help="Agent user email")
    args = parser.parse_args()
    asyncio.run(main(args.email))
