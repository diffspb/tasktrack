"""
Create (or reuse) an MCP agent user and add it to all existing projects.

Usage:
    cd backend
    python scripts/bootstrap_agent_user.py

Output: MCP_AGENT_USER_ID=<uuid>  — paste into .env.dev / .env.prod
"""

import asyncio
import sys
import os

# Run from backend/ directory so .env.dev is found
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from sqlalchemy import select

from app.core.config import settings
from app.core.db import SessionLocal
from app.models.project import Project, ProjectMember, ProjectMemberRole
from app.models.user import User


async def main() -> None:
    async with SessionLocal() as session:
        # Find or create agent user
        user = await session.scalar(
            select(User).where(User.email == "agent@tasktrack")
        )
        if user is None:
            user = User(
                email="agent@tasktrack",
                display_name="MCP Agent",
                keycloak_id="agent-mcp-stub",
                is_active=True,
            )
            session.add(user)
            await session.flush()
            print(f"Created agent user: {user.id}")
        else:
            print(f"Agent user already exists: {user.id}")

        # Add agent to all non-archived projects where not already a member
        projects = list((await session.scalars(
            select(Project).where(Project.is_archived.is_(False), Project.deleted_at.is_(None))
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
    print(f"\nMCP_AGENT_USER_ID={user.id}")
    print("\nAdd to .env.dev (and .env.prod):")
    print(f"  MCP_AGENT_USER_ID={user.id}")


if __name__ == "__main__":
    asyncio.run(main())
