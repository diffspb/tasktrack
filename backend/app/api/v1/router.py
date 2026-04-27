from fastapi import APIRouter

from app.api.v1 import health, projects

router = APIRouter(prefix="/api/v1")
router.include_router(health.router, tags=["health"])
router.include_router(projects.router)
