import asyncio
import json
from collections import defaultdict
from contextlib import asynccontextmanager
from typing import AsyncGenerator


class EventBus:
    def __init__(self) -> None:
        self._subscribers: dict[str, list[asyncio.Queue]] = defaultdict(list)

    def publish(self, project_id: str, event: dict) -> None:
        for q in self._subscribers.get(project_id, []):
            try:
                q.put_nowait(event)
            except asyncio.QueueFull:
                pass  # slow client — drop rather than block publisher

    @asynccontextmanager
    async def subscribe(self, project_id: str) -> AsyncGenerator[asyncio.Queue, None]:
        q: asyncio.Queue = asyncio.Queue(maxsize=100)
        self._subscribers[project_id].append(q)
        try:
            yield q
        finally:
            self._subscribers[project_id].remove(q)
            if not self._subscribers[project_id]:
                del self._subscribers[project_id]


event_bus = EventBus()


def make_task_event(event_type: str, task, project_id: str) -> dict:
    from app.schemas.task import TaskResponse
    return {
        "type": event_type,
        "project_id": project_id,
        "task_id": str(task.id),
        "task": json.loads(TaskResponse.model_validate(task).model_dump_json()),
    }
