import json

from app.mcp.schemas.workflow import workflow_detail
from app.mcp.utils import McpSession, parse_uuid, svc_call
from app.services import workflow_service


@svc_call
async def list_workflows(project_id: str) -> str:
    """
    List all workflows configured for a project.

    Each workflow includes: id, name, is_default, statuses (sorted by position),
    transitions (allowed moves between statuses).

    Use status ids from here when calling transition_task_status.
    """
    async with McpSession() as (session, user):
        pid = parse_uuid(project_id, "project_id")
        workflows = await workflow_service.list_workflows(session, pid, user)
        return json.dumps([workflow_detail(wf) for wf in workflows])


@svc_call
async def get_workflow(workflow_id: str) -> str:
    """
    Get full details of a specific workflow by UUID.

    Returns: id, name, is_default, project_id,
    statuses (id, name, category, is_default, position, color),
    transitions (id, from_status_id, to_status_id, required_role).

    Status categories: "initial" | "intermediate" | "final".
    Transitioning to a "final" status requires resolution_id.
    """
    async with McpSession() as (session, user):
        wid = parse_uuid(workflow_id, "workflow_id")
        wf = await workflow_service.get_workflow(session, wid, user)
        return json.dumps(workflow_detail(wf))
