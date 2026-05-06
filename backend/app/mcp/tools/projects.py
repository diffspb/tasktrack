import json

from app.mcp.schemas.project import project_detail, project_list_item
from app.mcp.utils import McpSession, parse_uuid, svc_call
from app.services import project_service


@svc_call
async def list_projects() -> str:
    """
    Return all projects visible to the agent.

    Each item: id, key, name, description, visibility, is_archived, member_count.
    Use the project id as input to other tools.
    """
    async with McpSession() as (session, user):
        projects = await project_service.list_projects(session, user)
        return json.dumps([project_list_item(p) for p in projects])


@svc_call
async def get_project(project_id: str) -> str:
    """
    Get full project details by UUID.

    Returns: id, key, name, description, visibility, owner_id, is_archived,
    version, members (list of {user_id, role}).

    Raises error if project not found or agent has no access.
    """
    async with McpSession() as (session, user):
        pid = parse_uuid(project_id, "project_id")
        project = await project_service.get_project(session, pid, user)
        return json.dumps(project_detail(project))
