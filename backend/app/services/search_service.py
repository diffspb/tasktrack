"""Full-text search across Tasks via Postgres tsvector (russian)."""
import uuid

from sqlalchemy import bindparam, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.project import ProjectMember, ProjectVisibility, Project
from app.models.task import Task
from app.models.user import User


async def search_tasks(
    session: AsyncSession,
    *, q: str,
    user: User,
    project_id: uuid.UUID | None = None,
    limit: int = 50,
) -> list[dict]:
    """
    Returns task summaries the user is allowed to see, ranked by ts_rank.
    `highlight` field is generated via ts_headline.
    """
    if not q.strip():
        return []

    member_subq = select(ProjectMember.project_id).where(ProjectMember.user_id == user.id)
    visibility_cond = (
        (Project.visibility == ProjectVisibility.public)
        | (Project.id.in_(member_subq))
    )

    tsquery = func.plainto_tsquery("russian", bindparam("q", q))
    rank = func.ts_rank(Task.search_vector, tsquery).label("rank")
    highlight = func.ts_headline(
        "russian",
        func.concat(Task.title, " ", func.coalesce(Task.description, "")),
        tsquery,
        "MaxFragments=2, MinWords=3, MaxWords=15",
    ).label("highlight")

    stmt = (
        select(Task, Project, rank, highlight)
        .join(Project, Project.id == Task.project_id)
        .where(
            Task.deleted_at.is_(None),
            Project.deleted_at.is_(None),
            Project.is_archived.is_(False),
            visibility_cond,
            Task.search_vector.op("@@")(tsquery),
        )
        .order_by(rank.desc())
        .limit(limit)
    )
    if project_id:
        stmt = stmt.where(Task.project_id == project_id)

    rows = (await session.execute(stmt)).all()
    return [
        {
            "id": t.id, "key": t.key, "title": t.title,
            "current_status_id": str(t.current_status_id),
            "project": {"id": p.id, "key": p.key, "name": p.name},
            "highlight": h,
        }
        for t, p, _, h in rows
    ]
