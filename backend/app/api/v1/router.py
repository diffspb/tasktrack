from fastapi import APIRouter

from app.api.v1 import (
    board_columns, comments, dev, health, notifications, projects, search,
    tasks, users, workflows,
)

router = APIRouter(prefix="/api/v1")
router.include_router(health.router, tags=["health"])
router.include_router(projects.router)
router.include_router(workflows.router)
router.include_router(board_columns.router)
router.include_router(tasks.router)
router.include_router(comments.router)
router.include_router(users.router)
router.include_router(notifications.router)
router.include_router(search.router)
router.include_router(dev.router)
