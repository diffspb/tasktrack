from __future__ import annotations

from typing import Any

from app.models.comment import Comment


def comment_out(c: Comment, replies: list[Comment] | None = None) -> dict[str, Any]:
    return {
        "id": str(c.id),
        "task_id": str(c.task_id),
        "author_id": str(c.author_id),
        "parent_comment_id": str(c.parent_comment_id) if c.parent_comment_id else None,
        "content": c.content,
        "labels": c.labels or [],
        "edited_at": c.edited_at.isoformat() if c.edited_at else None,
        "deleted_at": c.deleted_at.isoformat() if c.deleted_at else None,
        "created_at": c.created_at.isoformat(),
        "replies": [comment_out(r) for r in (replies or [])],
    }
