import json

from mcp.server.fastmcp.server import Context

from app.mcp.schemas.comment import comment_out
from app.mcp.utils import McpSession, parse_uuid, svc_call
from app.schemas.comment import CommentCreate, CommentUpdate
from app.services import comment_service


@svc_call
async def list_comments(ctx: Context, task_id: str) -> str:
    """
    List all top-level comments on a task, including their replies.

    Each comment: id, task_id, author_id, content, labels, edited_at,
    deleted_at, created_at, replies.

    Label "solution" marks a subtask solution submission that unblocks
    a parent decision task.
    """
    async with McpSession(ctx) as (session, user):
        tid = parse_uuid(task_id, "task_id")
        comments = await comment_service.list_comments(session, tid, user)
        return json.dumps([
            comment_out(c, replies=list(c.replies) if hasattr(c, "replies") else [])
            for c in comments
        ])


@svc_call
async def add_comment(
    ctx: Context,
    task_id: str,
    content: str,
    labels: list[str] | None = None,
    parent_comment_id: str | None = None,
) -> str:
    """
    Post a comment on a task.

    labels: string tags, e.g. ["solution"] to mark this as a Solution submission
    on a subtask — sets solution_comment_id in meta and contributes to unblocking
    a parent decision task.

    parent_comment_id: UUID of a top-level comment to reply to (max depth 1).
    """
    async with McpSession(ctx) as (session, user):
        tid = parse_uuid(task_id, "task_id")
        parent_id = parse_uuid(parent_comment_id, "parent_comment_id") if parent_comment_id else None
        data = CommentCreate(
            content=content,
            labels=labels or [],
            parent_comment_id=parent_id,
        )
        comment = await comment_service.create_comment(session, tid, data, user)
        return json.dumps(comment_out(comment))


@svc_call
async def update_comment(
    ctx: Context,
    comment_id: str,
    content: str,
) -> str:
    """
    Edit the text of an existing comment.

    Only the comment's author may edit it. Sets edited_at to the current time.
    Labels and parent_comment_id cannot be changed — repost if needed.

    Returns the updated comment.
    """
    async with McpSession(ctx) as (session, user):
        cid = parse_uuid(comment_id, "comment_id")
        data = CommentUpdate(content=content)
        comment = await comment_service.update_comment(session, cid, data, user)
        return json.dumps(comment_out(comment))
