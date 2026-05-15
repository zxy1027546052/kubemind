"""Session Runtime — orchestrates agent and tool runtimes for a single diagnosis session."""

from __future__ import annotations

from typing import Any

from app.runtime.agent_runtime import AgentRuntime
from app.runtime.event_bus import EventBus, event_bus_registry
from app.runtime.tool_runtime import ToolRuntime


class SessionRuntime:
    """Top-level runtime for a single ChatOps session, providing agent + tool tracking."""

    def __init__(self, session_id: str) -> None:
        self.session_id = session_id
        self.event_bus: EventBus = event_bus_registry.get_or_create(session_id)
        self.agent_runtime = AgentRuntime(session_id, self.event_bus)
        self.tool_runtime = ToolRuntime(session_id, self.event_bus)

    def emit(self, event_type: str, data: dict[str, Any] | None = None) -> None:
        self.event_bus.emit(event_type, data)

    def get_trace(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "agents": self.agent_runtime.get_summary(),
            "tools": self.tool_runtime.get_summary(),
            "total_duration_ms": self.agent_runtime.total_duration_ms,
            "total_tokens": self.agent_runtime.total_tokens,
            "event_count": len(self.event_bus.events),
        }

    def cleanup(self) -> None:
        event_bus_registry.remove(self.session_id)
