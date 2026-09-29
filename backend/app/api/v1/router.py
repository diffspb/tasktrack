from fastapi import APIRouter, Depends

from app.api.idempotency import idempotency_guard
from app.api.v1 import (
    admin, audit, comments, dev, gantt, health, link_types, notifications, projects, search,
    tasks, users, views, workflows,
)

router = APIRouter(prefix="/api/v1")
router.include_router(health.router, tags=["health"])
router.include_router(dev.router)

# Authenticated API: mutating requests may carry Idempotency-Key (ADR-019).
_idempotent = [Depends(idempotency_guard)]
for sub in (
    admin, projects, workflows, views, tasks, comments, users, notifications,
    search, link_types, gantt, audit,
):
    router.include_router(sub.router, dependencies=_idempotent)
