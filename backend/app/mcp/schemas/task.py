from __future__ import annotations

import uuid
from typing import Any

from app.models.task import Task, TaskLink
from app.models.workflow import Status, Transition


def task_list_item(task: Task, status: Status | None) -> dict[str, Any]:
    return {
        "id": str(task.id),
        "key": task.key,
        "title": task.title,
        "priority": task.priority.value if task.priority else None,
        "task_type_key": task.task_type.key if task.task_type else None,
        "task_type_name": task.task_type.name if task.task_type else None,
        "current_status_id": str(task.current_status_id),
        "current_status_name": status.name if status else None,
        "current_status_category": status.category.value if status else None,
        "assignee_id": str(task.assignee_id) if task.assignee_id else None,
        "parent_task_id": str(task.parent_task_id) if task.parent_task_id else None,
        "due_date": task.due_date.isoformat() if task.due_date else None,
        "version": task.version,
    }


def _format_link(link: TaskLink, task_id: uuid.UUID) -> dict[str, Any]:
    is_source = link.source_task_id == task_id
    other = link.target_task if is_source else link.source_task
    lt = link.link_type
    return {
        "link_id": str(link.id),
        "direction": "outward" if is_source else "inward",
        "relation": lt.outward_name if is_source else lt.inward_name,
        "link_type_name": lt.name,
        "task_id": str(other.id),
        "task_key": other.key,
        "task_title": other.title,
    }


def task_detail(
    task: Task,
    status: Status,
    transitions: list[Transition],
    links: list[TaskLink] | None = None,
) -> dict[str, Any]:
    is_decision = bool(task.task_type and task.task_type.key == "decision")
    subtask_ids = [str(st.id) for st in (task.subtasks or []) if st.deleted_at is None]

    available = [
        {
            "status_id": str(t.to_status_id),
            "status_name": t.to_status.name if t.to_status else None,
            "status_category": t.to_status.category.value if t.to_status else None,
        }
        for t in transitions
    ]

    return {
        "id": str(task.id),
        "key": task.key,
        "project_id": str(task.project_id),
        "workflow_id": str(task.workflow_id),
        "task_type_key": task.task_type.key if task.task_type else None,
        "task_type_name": task.task_type.name if task.task_type else None,
        "reporter_id": str(task.reporter_id),
        "assignee_id": str(task.assignee_id) if task.assignee_id else None,
        "parent_task_id": str(task.parent_task_id) if task.parent_task_id else None,
        "current_status_id": str(task.current_status_id),
        "current_status_name": status.name,
        "current_status_category": status.category.value,
        "title": task.title,
        "description": task.description,
        "priority": task.priority.value if task.priority else None,
        "meta": task.meta,
        "due_date": task.due_date.isoformat() if task.due_date else None,
        "version": task.version,
        "created_at": task.created_at.isoformat(),
        "updated_at": task.updated_at.isoformat(),
        "subtask_count": len(subtask_ids),
        "subtask_ids": subtask_ids,
        "available_transitions": available,
        "is_decision_task": is_decision,
        "links": [_format_link(l, task.id) for l in (links or [])],
    }
