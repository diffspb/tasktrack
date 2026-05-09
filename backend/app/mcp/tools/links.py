import json
import uuid as _uuid

from mcp.server.fastmcp.server import Context
from sqlalchemy import select

from app.mcp.utils import McpSession, parse_uuid, svc_call
from app.models.link_type import LinkType
from app.schemas.task import TaskLinkCreate
from app.services import task_link_service


@svc_call
async def create_task_link(
    ctx: Context,
    task_id: str,
    target_task_id: str,
    link_type_name: str,
    direction: str = "outward",
) -> str:
    """
    Create a link between two tasks.

    task_id: UUID of the source task (the one performing the action).
    target_task_id: UUID of the task to link to.
    link_type_name: name of the link type, e.g. "blocks", "depends_on",
                    "relates_to", "duplicates", "clones".
    direction: "outward" (default) or "inward".
      - outward: task_id [outward_name] target_task_id
                 e.g. task_id "blocks" target_task_id
      - inward:  target_task_id [outward_name] task_id
                 e.g. task_id "is blocked by" target_task_id
                 (internally swaps source/target)

    Returns a summary of the created link.
    """
    async with McpSession(ctx) as (session, user):
        tid = parse_uuid(task_id, "task_id")
        other_id = parse_uuid(target_task_id, "target_task_id")

        lt = await session.scalar(
            select(LinkType).where(
                LinkType.name == link_type_name.lower(),
                LinkType.is_active.is_(True),
            )
        )
        if not lt:
            available = list((await session.scalars(
                select(LinkType.name).where(LinkType.is_active.is_(True))
            )).all())
            return json.dumps({
                "error": f"Link type '{link_type_name}' not found.",
                "available": available,
            })

        if direction == "inward":
            source_id, target_id = other_id, tid
        else:
            source_id, target_id = tid, other_id

        data = TaskLinkCreate(target_task_id=target_id, link_type_id=lt.id)
        link = await task_link_service.create_task_link(session, source_id, data, user)

        is_source = link.source_task_id == tid
        other = link.target_task if is_source else link.source_task
        relation = lt.outward_name if is_source else lt.inward_name
        return json.dumps({
            "link_id": str(link.id),
            "relation": relation,
            "task_key": other.key,
            "task_title": other.title,
        })


@svc_call
async def delete_task_link(
    ctx: Context,
    task_id: str,
    link_id: str,
) -> str:
    """
    Delete a task link by its link_id.

    task_id: UUID of either the source or target task of the link.
    link_id: UUID of the link to delete (visible in get_task response → links[].link_id).

    Returns {"deleted": true} on success.
    """
    async with McpSession(ctx) as (session, user):
        tid = parse_uuid(task_id, "task_id")
        lid = parse_uuid(link_id, "link_id")
        await task_link_service.delete_task_link(session, tid, lid, user)
        return json.dumps({"deleted": True})
