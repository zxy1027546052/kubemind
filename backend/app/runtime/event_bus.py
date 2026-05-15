"""Event Bus — in-memory pub/sub for runtime events, consumed by SSE endpoints."""

from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass
class RuntimeEvent:
    """A single event emitted by the runtime layer."""

    type: str
    data: dict[str, Any]
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_sse(self) -> str:
        payload = json.dumps(
            {"timestamp": self.timestamp, **self.data},
            ensure_ascii=False,
        )
        return f"event: {self.type}\ndata: {payload}\n\n"


class EventBus:
    """Session-scoped event bus that collects events and feeds SSE streams."""

    def __init__(self, session_id: str) -> None:
        self.session_id = session_id
        self._events: list[RuntimeEvent] = []
        self._subscribers: list[asyncio.Queue[RuntimeEvent]] = []

    def emit(self, event_type: str, data: dict[str, Any] | None = None) -> RuntimeEvent:
        event = RuntimeEvent(type=event_type, data=data or {})
        self._events.append(event)
        for queue in self._subscribers:
            try:
                queue.put_nowait(event)
            except asyncio.QueueFull:
                pass
        return event

    def subscribe(self) -> asyncio.Queue[RuntimeEvent]:
        queue: asyncio.Queue[RuntimeEvent] = asyncio.Queue(maxsize=256)
        self._subscribers.append(queue)
        return queue

    def unsubscribe(self, queue: asyncio.Queue[RuntimeEvent]) -> None:
        self._subscribers = [q for q in self._subscribers if q is not queue]

    @property
    def events(self) -> list[RuntimeEvent]:
        return list(self._events)

    def to_sse_history(self) -> list[str]:
        return [e.to_sse() for e in self._events]


class EventBusRegistry:
    """Global registry mapping session_id -> EventBus."""

    def __init__(self) -> None:
        self._buses: dict[str, EventBus] = {}

    def get_or_create(self, session_id: str) -> EventBus:
        if session_id not in self._buses:
            self._buses[session_id] = EventBus(session_id)
        return self._buses[session_id]

    def remove(self, session_id: str) -> None:
        self._buses.pop(session_id, None)


event_bus_registry = EventBusRegistry()
