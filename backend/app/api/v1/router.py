from fastapi import APIRouter, Depends

from app.api.idempotency import idempotency_guard
from app.api.task_session import task_session_guard
from app.api.v1 import (
    admin, audit, comments, control, dev, external, gantt, health, link_types, notifications, portfolio,
    projects, results, search, sessions, tasks, users, views, work_packages, workflows,
)

router = APIRouter(prefix="/api/v1")
router.include_router(health.router, tags=["health"])
router.include_router(dev.router)

# Authenticated API: mutating requests may carry Idempotency-Key (ADR-019),
# any request may name the caller's work session in X-Task-Session (ADR-022).
_guards = [Depends(task_session_guard), Depends(idempotency_guard)]
for sub in (
    admin, projects, workflows, views, tasks, comments, users, notifications,
    search, link_types, gantt, audit, work_packages, results, sessions, control, external, portfolio,
):
    router.include_router(sub.router, dependencies=_guards)
