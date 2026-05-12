"""
Idempotent bootstrap of system-level reference data.
Called from app lifespan on every startup. Safe to run on a non-empty DB.
"""
import logging

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import SessionLocal

logger = logging.getLogger(__name__)


async def ensure_system_data() -> None:
    async with SessionLocal() as session:
        changed = False
        changed |= await _ensure_link_types(session)
        changed |= await _ensure_system_workflows(session)
        if changed:
            await session.commit()
            logger.info("System bootstrap complete.")


async def _ensure_link_types(session: AsyncSession) -> bool:
    from app.models.link_type import LinkType

    count = await session.scalar(select(func.count()).select_from(LinkType))
    if count:
        return False

    logger.info("Bootstrapping system link types...")
    session.add_all([
        LinkType(name="blocks",     outward_name="blocks",     inward_name="is blocked by",
                 is_directed=True,  color="#ef4444", constraint={"type": "blocking"}, position=0),
        LinkType(name="depends_on", outward_name="depends on", inward_name="is dependency of",
                 is_directed=True,  color="#f59e0b", constraint={"type": "sequential", "mode": "finish_to_start"}, position=1),
        LinkType(name="relates_to", outward_name="relates to", inward_name="relates to",
                 is_directed=False, color="#6366f1", constraint=None, position=2),
        LinkType(name="duplicates", outward_name="duplicates", inward_name="is duplicated by",
                 is_directed=True,  color="#8b5cf6", constraint=None, position=3),
        LinkType(name="clones",     outward_name="clones",     inward_name="is cloned by",
                 is_directed=True,  color="#10b981", constraint=None, position=4),
    ])
    await session.flush()
    return True


async def _ensure_system_workflows(session: AsyncSession) -> bool:
    from app.models.task_type import TaskType
    from app.models.workflow import Workflow, Status, StatusCategory, Transition

    count = await session.scalar(
        select(func.count()).select_from(TaskType).where(TaskType.is_system.is_(True))
    )
    if count:
        return False

    logger.info("Bootstrapping system workflows and task types...")

    wf_task_story = Workflow(name="Task/Story",       is_default=False)
    wf_bug        = Workflow(name="Bug",              is_default=False)
    wf_epic       = Workflow(name="Epic",             is_default=False)
    wf_decision   = Workflow(name="Decision Process", is_default=False)
    session.add_all([wf_task_story, wf_bug, wf_epic, wf_decision])
    await session.flush()

    _i, _m, _f = StatusCategory.initial, StatusCategory.intermediate, StatusCategory.final

    st_ts = [
        Status(workflow_id=wf_task_story.id, name="To Do",       category=_i, is_default=True,  position=0),
        Status(workflow_id=wf_task_story.id, name="In Progress", category=_m, is_default=False, position=1),
        Status(workflow_id=wf_task_story.id, name="Review",      category=_m, is_default=False, position=2),
        Status(workflow_id=wf_task_story.id, name="Done",        category=_f, is_default=False, position=3),
    ]
    st_bug = [
        Status(workflow_id=wf_bug.id, name="Open",        category=_i, is_default=True,  position=0),
        Status(workflow_id=wf_bug.id, name="In Progress", category=_m, is_default=False, position=1),
        Status(workflow_id=wf_bug.id, name="Review",      category=_m, is_default=False, position=2),
        Status(workflow_id=wf_bug.id, name="Verified",    category=_m, is_default=False, position=3),
        Status(workflow_id=wf_bug.id, name="Closed",      category=_f, is_default=False, position=4),
    ]
    st_epic = [
        Status(workflow_id=wf_epic.id, name="Planning", category=_i, is_default=True,  position=0),
        Status(workflow_id=wf_epic.id, name="Active",   category=_m, is_default=False, position=1),
        Status(workflow_id=wf_epic.id, name="Done",     category=_f, is_default=False, position=2),
    ]
    st_dec = [
        Status(workflow_id=wf_decision.id, name="Open",              category=_i, is_default=True,  position=0),
        Status(workflow_id=wf_decision.id, name="Collecting",        category=_m, is_default=False, position=1),
        Status(workflow_id=wf_decision.id, name="Awaiting Decision", category=_m, is_default=False, position=2),
        Status(workflow_id=wf_decision.id, name="Decided",           category=_f, is_default=False, position=3),
    ]
    session.add_all(st_ts + st_bug + st_epic + st_dec)
    await session.flush()

    def _linear(wf_id, statuses):
        return [
            Transition(workflow_id=wf_id, from_status_id=statuses[i].id, to_status_id=statuses[i + 1].id)
            for i in range(len(statuses) - 1)
        ]

    session.add_all(
        _linear(wf_task_story.id, st_ts) +
        [Transition(workflow_id=wf_task_story.id, from_status_id=st_ts[1].id, to_status_id=st_ts[0].id)] +
        _linear(wf_bug.id, st_bug) +
        [Transition(workflow_id=wf_bug.id, from_status_id=st_bug[1].id, to_status_id=st_bug[0].id)] +
        _linear(wf_epic.id, st_epic) +
        _linear(wf_decision.id, st_dec)
    )

    session.add_all([
        TaskType(key="task",     name="Задача",   is_system=True, icon="check-square", color="#6366f1", default_workflow_id=wf_task_story.id),
        TaskType(key="bug",      name="Баг",      is_system=True, icon="bug",          color="#ef4444", default_workflow_id=wf_bug.id),
        TaskType(key="story",    name="История",  is_system=True, icon="book-open",    color="#10b981", default_workflow_id=wf_task_story.id),
        TaskType(key="epic",     name="Эпик",     is_system=True, icon="zap",          color="#f59e0b", default_workflow_id=wf_epic.id),
        TaskType(key="decision", name="Decision", is_system=True, icon="git-branch",   color="#8b5cf6", default_workflow_id=wf_decision.id),
    ])
    await session.flush()
    return True
