from fastapi import APIRouter

from app.api.v1 import (
    decisions, dev, health, notifications, projects, resolutions, search,
    solutions, tasks, users, workflows,
)

router = APIRouter(prefix="/api/v1")
router.include_router(health.router, tags=["health"])
router.include_router(projects.router)
router.include_router(workflows.router)
router.include_router(resolutions.router)
router.include_router(tasks.router)
router.include_router(users.router)
router.include_router(solutions.router)
router.include_router(decisions.router)
router.include_router(notifications.router)
router.include_router(search.router)
router.include_router(dev.router)
