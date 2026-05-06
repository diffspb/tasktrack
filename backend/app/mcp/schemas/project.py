from __future__ import annotations

from typing import Any

from app.models.project import Project


def project_list_item(project: Project) -> dict[str, Any]:
    return {
        "id": str(project.id),
        "key": project.key,
        "name": project.name,
        "description": project.description,
        "visibility": project.visibility.value,
        "is_archived": project.is_archived,
        "member_count": len(project.members),
    }


def project_detail(project: Project) -> dict[str, Any]:
    return {
        **project_list_item(project),
        "owner_id": str(project.owner_id),
        "version": project.version,
        "created_at": project.created_at.isoformat(),
        "updated_at": project.updated_at.isoformat(),
        "members": [
            {"user_id": str(m.user_id), "role": m.role.value}
            for m in project.members
        ],
    }
