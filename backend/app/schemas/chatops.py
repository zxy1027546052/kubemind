from typing import Any

from pydantic import BaseModel, Field


class ChatOpsMessageRequest(BaseModel):
    session_id: str | None = Field(default=None)
    message: str = Field(min_length=1, max_length=5000)


class ChatOpsMessageResponse(BaseModel):
    session_id: str
    intent: str
    entities: dict[str, str]
    reply: str
    trace: list[dict[str, Any]]
    evidence: list[dict[str, Any]]
    tool_calls: list[dict[str, Any]]
    root_causes: list[dict[str, Any]]
    remediation_plan: list[dict[str, Any]]
    requires_human_approval: bool
