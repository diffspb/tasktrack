"""Export and import a project snapshot (for testing and environment migration)."""
from __future__ import annotations

import uuid
from collections import defaultdict
from datetime import UTC, date as date_type, datetime
from typing import Any

from fastapi import HTTPException, status as http_status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.comment import Comment
from app.models.link_type import LinkType
from app.models.project import Project, ProjectMember, ProjectMemberRole
from app.models.task import Task, TaskLink
from app.models.task_type import TaskType
from app.models.user import User
from app.models.workflow import (
    ProjectTaskTypeConfig,
    Status,
    StatusCategory,
    Transition,
    View,
    ViewType,
    Workflow,
)
from app.services.permissions import require_project_access

EXPORT_VERSION = 1


# ─────────────────────────── export ──────────────────────────────────────────


async def export_project(
    session: AsyncSession,
    project_id: uuid.UUID,
    user: User,
) -> dict[str, Any]:
    await require_project_access(session, project_id, user)

    project = await session.get(Project, project_id)
    if not project or project.deleted_at is not None:
        raise HTTPException(http_status.HTTP_404_NOT_FOUND, {"code": "PROJECT_NOT_FOUND"})

    # --- workflows ---
    workflows_raw = list((await session.scalars(
        select(Workflow)
        .options(selectinload(Workflow.statuses), selectinload(Workflow.transitions))
        .where(Workflow.project_id == project_id)
    )).all())

    status_name_map: dict[uuid.UUID, str] = {
        s.id: s.name for wf in workflows_raw for s in wf.statuses
    }
    workflow_name_map: dict[uuid.UUID, str] = {wf.id: wf.name for wf in workflows_raw}

    workflows_out = []
    for wf in workflows_raw:
        workflows_out.append({
            "name": wf.name,
            "is_default": wf.is_default,
            "statuses": [
                {
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
                    "from_status": status_name_map[t.from_status_id],
                    "to_status": status_name_map[t.to_status_id],
                    "required_role": t.required_role,
                }
                for t in wf.transitions
            ],
        })

    # --- task_type_configs ---
    configs = list((await session.scalars(
        select(ProjectTaskTypeConfig)
        .where(ProjectTaskTypeConfig.project_id == project_id)
    )).all())

    config_tt_ids = {c.task_type_id for c in configs}
    task_types_map: dict[uuid.UUID, TaskType] = {}
    if config_tt_ids:
        task_types_map = {
            tt.id: tt
            for tt in (await session.scalars(
                select(TaskType).where(TaskType.id.in_(config_tt_ids))
            )).all()
        }

    task_type_configs_out = [
        {
            "task_type_key": task_types_map[c.task_type_id].key,
            "workflow_name": workflow_name_map.get(c.workflow_id, ""),
        }
        for c in configs
        if c.task_type_id in task_types_map and c.workflow_id in workflow_name_map
    ]

    # --- tasks ---
    tasks_raw = list((await session.scalars(
        select(Task)
        .options(selectinload(Task.task_type))
        .where(Task.project_id == project_id, Task.deleted_at.is_(None))
        .order_by(Task.created_at)
    )).all())

    task_ids = {t.id for t in tasks_raw}
    task_key_map: dict[uuid.UUID, str] = {t.id: t.key for t in tasks_raw}

    all_status_ids = {t.current_status_id for t in tasks_raw}
    all_statuses: dict[uuid.UUID, Status] = {}
    if all_status_ids:
        all_statuses = {
            s.id: s
            for s in (await session.scalars(
                select(Status).where(Status.id.in_(all_status_ids))
            )).all()
        }

    # --- task links (both ends must be within the project) ---
    links_out: list[dict] = []
    if task_ids:
        links_raw = list((await session.scalars(
            select(TaskLink)
            .options(selectinload(TaskLink.link_type))
            .where(
                TaskLink.source_task_id.in_(task_ids),
                TaskLink.target_task_id.in_(task_ids),
            )
        )).all())
        links_out = [
            {
                "source_task_key": task_key_map[lnk.source_task_id],
                "target_task_key": task_key_map[lnk.target_task_id],
                "link_type_name": lnk.link_type.name,
            }
            for lnk in links_raw
        ]

    # --- comments (top-level + replies, non-deleted) ---
    comments_by_task: dict[uuid.UUID, list[Comment]] = defaultdict(list)
    if task_ids:
        comments_raw = list((await session.scalars(
            select(Comment)
            .options(selectinload(Comment.replies))
            .where(
                Comment.task_id.in_(task_ids),
                Comment.parent_comment_id.is_(None),
                Comment.deleted_at.is_(None),
            )
            .order_by(Comment.created_at)
        )).all())
        for c in comments_raw:
            comments_by_task[c.task_id].append(c)

    # --- serialize tasks ---
    tasks_out = []
    for t in tasks_raw:
        s = all_statuses.get(t.current_status_id)
        comments = [
            {
                "content": c.content,
                "labels": c.labels or [],
                "created_at": c.created_at.isoformat(),
                "replies": [
                    {
                        "content": r.content,
                        "labels": r.labels or [],
                        "created_at": r.created_at.isoformat(),
                    }
                    for r in c.replies
                    if r.deleted_at is None
                ],
            }
            for c in comments_by_task.get(t.id, [])
        ]
        tasks_out.append({
            "key": t.key,
            "title": t.title,
            "description": t.description,
            "task_type_key": t.task_type.key if t.task_type else "task",
            "priority": t.priority.value,
            "workflow_name": workflow_name_map.get(t.workflow_id, ""),
            "status_name": s.name if s else "",
            "status_category": s.category.value if s else "initial",
            "parent_task_key": task_key_map.get(t.parent_task_id) if t.parent_task_id else None,
            "start_date": t.start_date.isoformat() if t.start_date else None,
            "due_date": t.due_date.isoformat() if t.due_date else None,
            "meta": t.meta or {},
            "comments": comments,
        })

    return {
        "version": EXPORT_VERSION,
        "exported_at": datetime.now(UTC).isoformat(),
        "project": {
            "name": project.name,
            "key": project.key,
            "description": project.description,
            "visibility": project.visibility.value,
        },
        "workflows": workflows_out,
        "task_type_configs": task_type_configs_out,
        "links": links_out,
        "tasks": tasks_out,
    }


# ─────────────────────────── import ──────────────────────────────────────────


async def import_project(
    session: AsyncSession,
    data: dict[str, Any],
    new_key: str,
    include_comments: bool,
    reset_statuses: bool,
    user: User,
) -> Project:
    new_key = new_key.strip().upper()
    if not new_key:
        raise HTTPException(http_status.HTTP_422_UNPROCESSABLE_ENTITY, {"code": "INVALID_KEY"})

    # Check key uniqueness
    if await session.scalar(
        select(Project).where(Project.key == new_key, Project.deleted_at.is_(None))
    ):
        raise HTTPException(http_status.HTTP_409_CONFLICT, {"code": "DUPLICATE_PROJECT_KEY"})

    proj_data = data.get("project", {})

    # 1. Bare project record (no auto-workflow — we'll restore from export data)
    project = Project(
        name=proj_data.get("name", new_key),
        key=new_key,
        description=proj_data.get("description"),
        visibility=proj_data.get("visibility", "restricted"),
        owner_id=user.id,
    )
    session.add(project)
    await session.flush()
    session.add(ProjectMember(
        project_id=project.id, user_id=user.id, role=ProjectMemberRole.admin,
    ))

    # 2. Workflows → statuses → transitions
    # workflow_name → (Workflow, {status_name: Status})
    workflow_map: dict[str, tuple[Workflow, dict[str, Status]]] = {}

    for wf_data in data.get("workflows", []):
        wf = Workflow(
            project_id=project.id,
            name=wf_data["name"],
            is_default=wf_data["is_default"],
        )
        session.add(wf)
        await session.flush()

        status_by_name: dict[str, Status] = {}
        for s_data in wf_data.get("statuses", []):
            s = Status(
                workflow_id=wf.id,
                name=s_data["name"],
                category=StatusCategory(s_data["category"]),
                is_default=s_data["is_default"],
                position=s_data["position"],
                color=s_data.get("color"),
            )
            session.add(s)
            status_by_name[s_data["name"]] = s
        await session.flush()

        for t_data in wf_data.get("transitions", []):
            src = status_by_name.get(t_data["from_status"])
            dst = status_by_name.get(t_data["to_status"])
            if src and dst:
                session.add(Transition(
                    workflow_id=wf.id,
                    from_status_id=src.id,
                    to_status_id=dst.id,
                    required_role=t_data.get("required_role"),
                ))

        workflow_map[wf_data["name"]] = (wf, status_by_name)

    await session.flush()

    # 3. Task type configs
    for cfg in data.get("task_type_configs", []):
        task_type = await session.scalar(
            select(TaskType)
            .where(TaskType.key == cfg["task_type_key"])
            .order_by(TaskType.project_id.nulls_last())
        )
        wf_entry = workflow_map.get(cfg["workflow_name"])
        if task_type and wf_entry:
            wf_obj, _ = wf_entry
            session.add(ProjectTaskTypeConfig(
                project_id=project.id,
                task_type_id=task_type.id,
                workflow_id=wf_obj.id,
            ))

    await session.flush()

    # 4. Default views so Kanban board works
    session.add(View(
        project_id=project.id, name="Board", type=ViewType.kanban, position=0, is_default=True,
    ))
    session.add(View(
        project_id=project.id, name="Backlog", type=ViewType.backlog, position=1,
    ))

    # 5. Tasks in topological order (parents before children)
    tasks_data = data.get("tasks", [])
    old_key_to_task: dict[str, Task] = {}
    task_counter = 0

    for t_data in _topo_sort(tasks_data):
        wf_name = t_data.get("workflow_name", "")
        wf_entry = workflow_map.get(wf_name) or _default_workflow_entry(workflow_map)
        if not wf_entry:
            raise HTTPException(
                http_status.HTTP_422_UNPROCESSABLE_ENTITY,
                {"code": "NO_WORKFLOW_IN_EXPORT"},
            )
        wf_obj, status_by_name = wf_entry

        # Status resolution
        if reset_statuses:
            current_status = _initial_status(status_by_name)
        else:
            current_status = (
                status_by_name.get(t_data.get("status_name", ""))
                or _initial_status(status_by_name)
            )

        if not current_status:
            raise HTTPException(
                http_status.HTTP_422_UNPROCESSABLE_ENTITY,
                {"code": "CANNOT_RESOLVE_STATUS", "task_key": t_data.get("key")},
            )

        # Task type
        task_type = await session.scalar(
            select(TaskType)
            .where(TaskType.key == t_data.get("task_type_key", "task"))
            .order_by(TaskType.project_id.nulls_last())
        )
        if not task_type:
            task_type = await session.scalar(
                select(TaskType).where(TaskType.key == "task")
                .order_by(TaskType.project_id.nulls_last())
            )

        # Parent reference
        parent_id: uuid.UUID | None = None
        parent_key = t_data.get("parent_task_key")
        if parent_key and parent_key in old_key_to_task:
            parent_id = old_key_to_task[parent_key].id

        task_counter += 1
        task = Task(
            project_id=project.id,
            workflow_id=wf_obj.id,
            task_type_id=task_type.id if task_type else None,
            reporter_id=user.id,
            assignee_id=None,
            parent_task_id=parent_id,
            current_status_id=current_status.id,
            key=f"{new_key}-{task_counter}",
            title=t_data["title"],
            description=t_data.get("description"),
            priority=t_data.get("priority", "medium"),
            start_date=date_type.fromisoformat(t_data["start_date"]) if t_data.get("start_date") else None,
            due_date=date_type.fromisoformat(t_data["due_date"]) if t_data.get("due_date") else None,
            meta=t_data.get("meta") or {},
        )
        session.add(task)
        await session.flush()
        old_key_to_task[t_data["key"]] = task

    # 6. Task links
    lt_cache: dict[str, LinkType | None] = {}
    for lnk in data.get("links", []):
        src = old_key_to_task.get(lnk["source_task_key"])
        dst = old_key_to_task.get(lnk["target_task_key"])
        if not src or not dst:
            continue
        lt_name = lnk["link_type_name"]
        if lt_name not in lt_cache:
            lt_cache[lt_name] = await session.scalar(
                select(LinkType).where(
                    LinkType.name == lt_name,
                    LinkType.is_active.is_(True),
                )
            )
        lt = lt_cache[lt_name]
        if lt:
            session.add(TaskLink(
                source_task_id=src.id,
                target_task_id=dst.id,
                link_type_id=lt.id,
                created_by=user.id,
            ))

    # 7. Comments (optional)
    if include_comments:
        for t_data in tasks_data:
            task = old_key_to_task.get(t_data["key"])
            if not task:
                continue
            for c_data in t_data.get("comments", []):
                parent_comment = Comment(
                    task_id=task.id,
                    author_id=user.id,
                    content=c_data["content"],
                    labels=c_data.get("labels") or [],
                )
                session.add(parent_comment)
                await session.flush()
                for r_data in c_data.get("replies", []):
                    session.add(Comment(
                        task_id=task.id,
                        author_id=user.id,
                        parent_comment_id=parent_comment.id,
                        content=r_data["content"],
                        labels=r_data.get("labels") or [],
                    ))

    await session.commit()

    result = await session.scalar(
        select(Project)
        .options(selectinload(Project.members))
        .where(Project.id == project.id)
    )
    return result  # type: ignore[return-value]


# ─────────────────────────── helpers ─────────────────────────────────────────


def _topo_sort(tasks_data: list[dict]) -> list[dict]:
    """Return tasks ordered so parents always appear before their children."""
    remaining = {t["key"]: t for t in tasks_data}
    result: list[dict] = []
    while remaining:
        progress = False
        for key in list(remaining):
            parent_key = remaining[key].get("parent_task_key")
            if not parent_key or parent_key not in remaining:
                result.append(remaining.pop(key))
                progress = True
        if not progress:
            result.extend(remaining.values())
            break
    return result


def _initial_status(status_by_name: dict[str, Status]) -> Status | None:
    """Return is_default+initial status, or any initial status, or first."""
    for s in status_by_name.values():
        if s.is_default and s.category == StatusCategory.initial:
            return s
    for s in status_by_name.values():
        if s.category == StatusCategory.initial:
            return s
    return next(iter(status_by_name.values()), None)


def _default_workflow_entry(
    workflow_map: dict[str, tuple[Workflow, dict[str, Status]]],
) -> tuple[Workflow, dict[str, Status]] | None:
    for wf, statuses in workflow_map.values():
        if wf.is_default:
            return wf, statuses
    return next(iter(workflow_map.values()), None)
