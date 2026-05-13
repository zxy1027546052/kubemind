from typing import Any, TypedDict
from uuid import uuid4


class OpsGraphState(TypedDict):
    session_id: str
    user_query: str
    intent: str
    entities: dict[str, str]
    time_range: dict[str, str]
    evidence: list[dict[str, Any]]
    tool_calls: list[dict[str, Any]]
    root_causes: list[dict[str, Any]]
    remediation_plan: list[dict[str, Any]]
    requires_human_approval: bool
    trace: list[dict[str, Any]]


def create_initial_state(session_id: str | None, user_query: str) -> OpsGraphState:
    return {
        "session_id": session_id or f"chat-{uuid4().hex[:12]}",
        "user_query": user_query,
        "intent": "unknown",
        "entities": {},
        "time_range": {},
        "evidence": [],
        "tool_calls": [],
        "root_causes": [],
        "remediation_plan": [],
        "requires_human_approval": False,
        "trace": [],
    }
