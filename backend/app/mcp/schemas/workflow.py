from __future__ import annotations

from typing import Any

from app.models.workflow import Workflow


def workflow_detail(wf: Workflow) -> dict[str, Any]:
    return {
        "id": str(wf.id),
        "project_id": str(wf.project_id) if wf.project_id else None,
        "name": wf.name,
        "is_default": wf.is_default,
        "statuses": [
            {
                "id": str(s.id),
                "name": s.name,
                "category": s.category.value,
                "is_default": s.is_default,
                "position": s.position,
                "color": s.color,
            }
            for s in sorted(wf.statuses, key=lambda s: s.position)
        ],
        "transitions": [
            {
                "id": str(t.id),
                "from_status_id": str(t.from_status_id),
                "to_status_id": str(t.to_status_id),
                "required_role": t.required_role,
            }
            for t in wf.transitions
        ],
    }
