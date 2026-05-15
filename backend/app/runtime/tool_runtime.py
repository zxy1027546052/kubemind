"""Tool Runtime — wraps tool invocations with lifecycle tracking and event emission."""

from __future__ import annotations

from typing import Any

from app.runtime.event_bus import EventBus
from app.runtime.models import ToolExecution

HIGH_RISK_TOOLS = {"kubectl_delete", "kubectl_scale", "kubectl_rollout_restart"}
MEDIUM_RISK_TOOLS = {"kubectl_apply", "kubectl_patch"}


def _classify_risk(tool_name: str) -> str:
    if tool_name in HIGH_RISK_TOOLS:
        return "high"
    if tool_name in MEDIUM_RISK_TOOLS:
        return "medium"
    return "low"


class ToolRuntime:
    """Manages ToolExecution lifecycle for a single session."""

    def __init__(self, session_id: str, event_bus: EventBus) -> None:
        self.session_id = session_id
        self.event_bus = event_bus
        self.executions: list[ToolExecution] = []

    def start_tool(
        self, tool_name: str, agent_execution_id: str, args: dict[str, Any] | None = None
    ) -> ToolExecution:
        risk = _classify_risk(tool_name)
        execution = ToolExecution(
            tool_name=tool_name,
            agent_execution_id=agent_execution_id,
            args=args or {},
            risk_level=risk,
            requires_approval=(risk == "high"),
        )
        execution.start()
        self.executions.append(execution)
        self.event_bus.emit("tool.started", {
            "tool": tool_name,
            "execution_id": execution.id,
            "agent_execution_id": agent_execution_id,
            "args": args or {},
            "risk_level": risk,
        })
        if execution.requires_approval:
            self.event_bus.emit("approval.required", {
                "tool": tool_name,
                "execution_id": execution.id,
                "risk_level": risk,
            })
        return execution

    def emit_stdout(self, execution: ToolExecution, chunk: str) -> None:
        execution.stdout += chunk
        self.event_bus.emit("tool.stdout", {
            "execution_id": execution.id,
            "tool": execution.tool_name,
            "chunk": chunk,
        })

    def complete_tool(self, execution: ToolExecution, stdout: str = "") -> None:
        execution.complete(stdout)
        self.event_bus.emit("tool.completed", {
            "tool": execution.tool_name,
            "execution_id": execution.id,
            "duration_ms": execution.duration_ms,
            "status": "success",
        })

    def fail_tool(self, execution: ToolExecution, stderr: str = "") -> None:
        execution.fail(stderr)
        self.event_bus.emit("tool.failed", {
            "tool": execution.tool_name,
            "execution_id": execution.id,
            "duration_ms": execution.duration_ms,
            "error": stderr,
        })

    def get_summary(self) -> list[dict[str, Any]]:
        return [e.to_dict() for e in self.executions]
