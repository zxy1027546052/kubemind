from typing import Any, TypedDict
from uuid import uuid4


class OpsGraphState(TypedDict):
    session_id: str
    user_query: str
    intent: str
    intents: list[str]
    entities: dict[str, str]
    time_range: dict[str, str]
    conversation_history: list[dict[str, str]]
    evidence: list[dict[str, Any]]
    tool_calls: list[dict[str, Any]]
    root_causes: list[dict[str, Any]]
    remediation_plan: list[dict[str, Any]]
    requires_human_approval: bool
    trace: list[dict[str, Any]]
    llm_reply: str


def create_initial_state(
    session_id: str | None,
    user_query: str,
    history: list[dict[str, str]] | None = None,
) -> OpsGraphState:
    return {
        "session_id": session_id or f"chat-{uuid4().hex[:12]}",
        "user_query": user_query,
        "intent": "unknown",
        "intents": [],
        "entities": {},
        "time_range": {},
        "conversation_history": history or [],
        "evidence": [],
        "tool_calls": [],
        "root_causes": [],
        "remediation_plan": [],
        "requires_human_approval": False,
        "trace": [],
        "llm_reply": "",
    }
