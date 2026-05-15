"""Runtime data models — AgentExecution & ToolExecution for tracking agent pipeline metadata."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Literal
from uuid import uuid4


@dataclass
class AgentExecution:
    """Tracks a single agent node execution within a session."""

    agent_name: str
    session_id: str
    id: str = field(default_factory=lambda: uuid4().hex[:16])
    status: Literal["pending", "running", "success", "failed", "skipped"] = "pending"
    started_at: datetime | None = None
    finished_at: datetime | None = None
    duration_ms: int | None = None
    input_data: dict[str, Any] = field(default_factory=dict)
    output_data: dict[str, Any] = field(default_factory=dict)
    token_usage: int = 0
    error: str | None = None
    tool_executions: list[str] = field(default_factory=list)

    def start(self) -> None:
        self.status = "running"
        self.started_at = datetime.now(timezone.utc)

    def complete(self, output: dict[str, Any] | None = None) -> None:
        self.status = "success"
        self.finished_at = datetime.now(timezone.utc)
        if self.started_at:
            self.duration_ms = int((self.finished_at - self.started_at).total_seconds() * 1000)
        if output:
            self.output_data = output

    def fail(self, error: str) -> None:
        self.status = "failed"
        self.error = error
        self.finished_at = datetime.now(timezone.utc)
        if self.started_at:
            self.duration_ms = int((self.finished_at - self.started_at).total_seconds() * 1000)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "session_id": self.session_id,
            "agent_name": self.agent_name,
            "status": self.status,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "finished_at": self.finished_at.isoformat() if self.finished_at else None,
            "duration_ms": self.duration_ms,
            "token_usage": self.token_usage,
            "error": self.error,
            "tool_executions": self.tool_executions,
        }


@dataclass
class ToolExecution:
    """Tracks a single tool invocation within an agent execution."""

    tool_name: str
    agent_execution_id: str
    args: dict[str, Any] = field(default_factory=dict)
    id: str = field(default_factory=lambda: uuid4().hex[:16])
    status: Literal["pending", "running", "success", "failed"] = "pending"
    stdout: str = ""
    stderr: str = ""
    duration_ms: int = 0
    risk_level: Literal["low", "medium", "high"] = "low"
    requires_approval: bool = False
    _start_time: float = field(default=0.0, repr=False)

    def start(self) -> None:
        self.status = "running"
        self._start_time = time.time()

    def complete(self, stdout: str = "") -> None:
        self.status = "success"
        self.stdout = stdout
        self.duration_ms = int((time.time() - self._start_time) * 1000)

    def fail(self, stderr: str = "") -> None:
        self.status = "failed"
        self.stderr = stderr
        self.duration_ms = int((time.time() - self._start_time) * 1000)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "agent_execution_id": self.agent_execution_id,
            "tool_name": self.tool_name,
            "args": self.args,
            "status": self.status,
            "stdout": self.stdout,
            "stderr": self.stderr,
            "duration_ms": self.duration_ms,
            "risk_level": self.risk_level,
            "requires_approval": self.requires_approval,
        }
