from sqlalchemy.orm import Session

from app.agents.graph import run_ops_graph_with_db
from app.agents.state import create_initial_state
from app.schemas.chatops import ChatOpsMessageRequest, ChatOpsMessageResponse


def handle_chatops_message(payload: ChatOpsMessageRequest, db: Session | None = None) -> ChatOpsMessageResponse:
    state = create_initial_state(session_id=payload.session_id, user_query=payload.message)
    result = run_ops_graph_with_db(state, db=db)
    return ChatOpsMessageResponse(
        session_id=result["session_id"],
        intent=result["intent"],
        entities=result["entities"],
        reply=_build_reply(result["intent"], result["entities"], result["requires_human_approval"]),
        trace=result["trace"],
        evidence=result["evidence"],
        tool_calls=result["tool_calls"],
        root_causes=result["root_causes"],
        remediation_plan=result["remediation_plan"],
        requires_human_approval=result["requires_human_approval"],
    )


def _build_reply(intent: str, entities: dict[str, str], requires_human_approval: bool) -> str:
    namespace = entities.get("namespace") or "默认命名空间"
    workload = entities.get("workload") or "目标对象"
    if intent == "query_metric":
        return f"已识别为指标查询，将查询 {namespace} 中 {workload} 的相关指标。"
    if intent == "query_logs":
        return f"已识别为日志查询，将检索 {namespace} 中 {workload} 的日志。"
    if intent == "search_runbook":
        return "已识别为 Runbook 检索，将从知识库召回相关处理手册。"
    if intent == "create_workflow":
        suffix = "该动作需要人工确认。" if requires_human_approval else ""
        return f"已识别为创建排查流程。{suffix}"
    if intent == "query_cluster":
        return "已识别为集群查询，将获取集群、节点和 Pod 概览。"
    return f"已识别为故障诊断，将围绕 {namespace} 中 {workload} 收集证据并生成根因候选。"
