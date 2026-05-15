"""Agent Runtime — wraps agent node execution with lifecycle tracking and event emission."""

from __future__ import annotations

from typing import Any

from app.runtime.event_bus import EventBus
from app.runtime.models import AgentExecution


class AgentRuntime:
    """Manages AgentExecution lifecycle for a single session."""

    def __init__(self, session_id: str, event_bus: EventBus) -> None:
        self.session_id = session_id
        self.event_bus = event_bus
        self.executions: list[AgentExecution] = []

    def start_agent(self, agent_name: str, input_data: dict[str, Any] | None = None) -> AgentExecution:
        execution = AgentExecution(
            agent_name=agent_name,
            session_id=self.session_id,
            input_data=input_data or {},
        )
        execution.start()
        self.executions.append(execution)
        self.event_bus.emit("agent.started", {
            "agent": agent_name,
            "execution_id": execution.id,
        })
        return execution

    def complete_agent(self, execution: AgentExecution, output: dict[str, Any] | None = None) -> None:
        execution.complete(output)
        self.event_bus.emit("agent.completed", {
            "agent": execution.agent_name,
            "execution_id": execution.id,
            "duration_ms": execution.duration_ms,
            "status": "success",
        })

    def fail_agent(self, execution: AgentExecution, error: str) -> None:
        execution.fail(error)
        self.event_bus.emit("agent.failed", {
            "agent": execution.agent_name,
            "execution_id": execution.id,
            "duration_ms": execution.duration_ms,
            "error": error,
        })

    def get_summary(self) -> list[dict[str, Any]]:
        return [e.to_dict() for e in self.executions]

    @property
    def total_duration_ms(self) -> int:
        return sum(e.duration_ms or 0 for e in self.executions)

    @property
    def total_tokens(self) -> int:
        return sum(e.token_usage for e in self.executions)
