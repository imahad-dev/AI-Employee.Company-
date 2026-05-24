from __future__ import annotations

import asyncio
from collections import defaultdict

from app.core.models import RunEvent


class EventBroker:
    def __init__(self) -> None:
        self._queues: dict[str, list[asyncio.Queue[RunEvent]]] = defaultdict(list)

    async def publish(self, event: RunEvent) -> None:
        if not self._queues.get(event.project_id):
            return
        for queue in list(self._queues[event.project_id]):
            await queue.put(event)

    async def subscribe(self, project_id: str):
        queue: asyncio.Queue[RunEvent] = asyncio.Queue()
        self._queues[project_id].append(queue)
        try:
            while True:
                yield await queue.get()
        finally:
            self._queues[project_id].remove(queue)


broker = EventBroker()
