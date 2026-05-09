from mcp.server.fastmcp import FastMCP

from app.mcp.tools import comments, links, projects, tasks, users, workflows

mcp = FastMCP(
    name="tasktrack",
    instructions=(
        "TaskTrack MCP server. Tools for managing projects, tasks, comments, workflows, and task links. "
        "Start with list_projects to discover available projects and their IDs. "
        "Use search_tasks for full-text lookup and search_users to resolve assignee_id by name or email. "
        "Always call get_task before update_task to obtain the current version field. "
        "Task links (relations) are included in get_task/get_task_by_key response under 'links'."
    ),
)

# Projects
mcp.add_tool(projects.list_projects)
mcp.add_tool(projects.get_project)

# Tasks
mcp.add_tool(tasks.list_tasks)
mcp.add_tool(tasks.get_task)
mcp.add_tool(tasks.get_task_by_key)
mcp.add_tool(tasks.list_my_tasks)
mcp.add_tool(tasks.search_tasks)
mcp.add_tool(tasks.create_task)
mcp.add_tool(tasks.update_task)
mcp.add_tool(tasks.transition_task_status)

# Users
mcp.add_tool(users.search_users)

# Comments
mcp.add_tool(comments.list_comments)
mcp.add_tool(comments.add_comment)
mcp.add_tool(comments.update_comment)

# Workflows (read-only)
mcp.add_tool(workflows.list_workflows)
mcp.add_tool(workflows.get_workflow)

# Task links
mcp.add_tool(links.create_task_link)
mcp.add_tool(links.delete_task_link)
