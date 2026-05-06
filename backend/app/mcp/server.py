from mcp.server.fastmcp import FastMCP

from app.mcp.tools import comments, projects, tasks, workflows

mcp = FastMCP(
    name="tasktrack",
    instructions=(
        "TaskTrack MCP server. Tools for managing projects, tasks, comments, and workflows. "
        "Start with list_projects to discover available projects and their IDs. "
        "Always call get_task before update_task to obtain the current version field."
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
mcp.add_tool(tasks.create_task)
mcp.add_tool(tasks.update_task)
mcp.add_tool(tasks.transition_task_status)

# Comments
mcp.add_tool(comments.list_comments)
mcp.add_tool(comments.add_comment)

# Workflows (read-only)
mcp.add_tool(workflows.list_workflows)
mcp.add_tool(workflows.get_workflow)
