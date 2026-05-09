from fastapi import APIRouter

from app.api.v1 import (
    comments, dev, gantt, health, link_types, notifications, projects, search,
    tasks, users, views, workflows,
)

router = APIRouter(prefix="/api/v1")
router.include_router(health.router, tags=["health"])
router.include_router(projects.router)
router.include_router(workflows.router)
router.include_router(views.router)
router.include_router(tasks.router)
router.include_router(comments.router)
router.include_router(users.router)
router.include_router(notifications.router)
router.include_router(search.router)
router.include_router(link_types.router)
router.include_router(gantt.router)
router.include_router(dev.router)
