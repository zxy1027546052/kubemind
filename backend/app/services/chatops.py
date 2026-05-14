import json
from collections.abc import Generator

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
        llm_reply=result.get("llm_reply", ""),
    )


def handle_chatops_message_stream(
    payload: ChatOpsMessageRequest, db: Session | None = None
) -> Generator[str, None, None]:
    """Run the agent graph and yield SSE events as agents progress."""
    from app.agents.nodes import (
        diagnosis_agent,
        milvus_agent,
        observability_agent,
        planner_agent,
        retriever_agent,
    )
    from app.services.llm import chat_completion_stream

    state = create_initial_state(session_id=payload.session_id, user_query=payload.message)

    # --- Planner ---
    state = planner_agent(state)
    yield _sse("agent_done", {"agent": "PlannerAgent", "intent": state["intent"], "entities": state["entities"]})

    # --- Retriever ---
    state = retriever_agent(state)
    yield _sse("agent_done", {"agent": "RetrieverAgent"})

    # --- Milvus ---
    state = milvus_agent(state, db=db)
    yield _sse("agent_done", {"agent": "MilvusAgent", "evidence_count": len(state["evidence"])})

    # --- Observability ---
    state = observability_agent(state)
    yield _sse("agent_done", {"agent": "ObservabilityAgent"})

    # --- Diagnosis with streaming LLM ---
    if db and state["intent"] in {"diagnose_issue", "search_runbook", "query_metric", "query_logs"}:
        evidence_text = "\n".join(
            f"[{e.get('source', '')}] {e.get('title', '')}: {e.get('summary', '')}"
            for e in state["evidence"][-10:]
        ) or "暂无证据"

        prompt = f"""你是一位云原生运维专家。根据以下信息为用户提供诊断建议。

用户问题：{state["user_query"]}
意图：{state["intent"]}
实体：{state["entities"]}
证据：
{evidence_text}

请用中文简要分析（200字以内），包含：可能原因、建议排查方向。"""
        try:
            for token in chat_completion_stream(
                db,
                messages=[
                    {"role": "system", "content": "你是云原生运维专家，回答简洁专业。"},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.3,
                max_tokens=512,
            ):
                yield _sse("token", {"content": token})
        except Exception:
            yield _sse("token", {"content": "[LLM 服务暂不可用]"})
    else:
        yield _sse("token", {"content": ""})

    # Build rule-based fallback diagnosis
    state = diagnosis_agent(state, db=None)  # don't call LLM again, already streamed
    state["llm_reply"] = ""  # already streamed token-by-token

    # --- Final done event ---
    final = ChatOpsMessageResponse(
        session_id=state["session_id"],
        intent=state["intent"],
        entities=state["entities"],
        reply=_build_reply(state["intent"], state["entities"], state["requires_human_approval"]),
        trace=state["trace"],
        evidence=state["evidence"],
        tool_calls=state["tool_calls"],
        root_causes=state["root_causes"],
        remediation_plan=state["remediation_plan"],
        requires_human_approval=state["requires_human_approval"],
        llm_reply="",
    )
    yield _sse("done", final.model_dump())


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
    if intent == "general_chat":
        return (
            "我是 KubeMind 智能运维助手，支持以下能力：\n"
            "• 指标查询 — 查询 CPU、内存等资源指标\n"
            "• 日志查询 — 检索服务错误日志\n"
            "• 故障诊断 — 分析故障现象并生成根因候选\n"
            "• Runbook 检索 — 从知识库召回相关处理手册\n"
            "• 集群查询 — 查看集群、节点、Pod 状态\n"
            "• 流程创建 — 生成标准化排查流程\n\n"
            "请用自然语言描述你的运维需求。"
        )
    return f"已识别为故障诊断，将围绕 {namespace} 中 {workload} 收集证据并生成根因候选。"


def _sse(event: str, data: dict | str) -> str:
    payload = json.dumps(data, ensure_ascii=False)
    return f"event: {event}\ndata: {payload}\n\n"
