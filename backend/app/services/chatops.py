import json
from collections.abc import Generator

from sqlalchemy.orm import Session

from app.agents.graph import run_ops_graph_with_db
from app.agents.state import create_initial_state
from app.runtime import SessionRuntime
from app.schemas.chatops import ChatOpsMessageRequest, ChatOpsMessageResponse


def handle_chatops_message(payload: ChatOpsMessageRequest, db: Session | None = None) -> ChatOpsMessageResponse:
    state = create_initial_state(session_id=payload.session_id, user_query=payload.message)
    result = run_ops_graph_with_db(state, db=db)
    return ChatOpsMessageResponse(
        session_id=result["session_id"],
        intent=result["intent"],
        entities=result["entities"],
        reply=_build_reply(
            result["intent"],
            result["entities"],
            result["requires_human_approval"],
            llm_reply=result.get("llm_reply", ""),
            evidence=result.get("evidence", []),
            tool_calls=result.get("tool_calls", []),
        ),
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
    """Run the agent graph and yield structured SSE events via Runtime Layer."""
    from app.agents.nodes import (
        diagnosis_agent,
        mcp_ops_agent,
        milvus_agent,
        observability_agent,
        planner_agent,
        retriever_agent,
    )
    from app.services.llm import chat_completion_stream

    state = create_initial_state(session_id=payload.session_id, user_query=payload.message)
    runtime = SessionRuntime(state["session_id"])

    # --- Planner ---
    exec_planner = runtime.agent_runtime.start_agent("PlannerAgent", {"query": state["user_query"]})
    yield _sse_event(runtime, "agent.started")
    try:
        state = planner_agent(state, db=db)
        runtime.agent_runtime.complete_agent(exec_planner, {"intent": state["intent"], "entities": state["entities"]})
    except Exception as e:
        runtime.agent_runtime.fail_agent(exec_planner, str(e))
    yield _sse_event(runtime, "agent.completed")

    # --- Retriever ---
    exec_retriever = runtime.agent_runtime.start_agent("RetrieverAgent")
    yield _sse_event(runtime, "agent.started")
    try:
        state = retriever_agent(state)
        runtime.agent_runtime.complete_agent(exec_retriever)
    except Exception as e:
        runtime.agent_runtime.fail_agent(exec_retriever, str(e))
    yield _sse_event(runtime, "agent.completed")

    # --- Milvus ---
    exec_milvus = runtime.agent_runtime.start_agent("MilvusAgent")
    yield _sse_event(runtime, "agent.started")
    try:
        state = milvus_agent(state, db=db)
        runtime.agent_runtime.complete_agent(exec_milvus, {"evidence_count": len(state["evidence"])})
    except Exception as e:
        runtime.agent_runtime.fail_agent(exec_milvus, str(e))
    yield _sse_event(runtime, "agent.completed")

    # --- Observability ---
    exec_obs = runtime.agent_runtime.start_agent("ObservabilityAgent")
    yield _sse_event(runtime, "agent.started")
    try:
        state = observability_agent(state)
        runtime.agent_runtime.complete_agent(exec_obs)
    except Exception as e:
        runtime.agent_runtime.fail_agent(exec_obs, str(e))
    yield _sse_event(runtime, "agent.completed")

    # --- MCP Ops Tools ---
    exec_mcp = runtime.agent_runtime.start_agent("McpOpsAgent")
    yield _sse_event(runtime, "agent.started")
    try:
        state = mcp_ops_agent(state, db=db)
        runtime.agent_runtime.complete_agent(exec_mcp, {"tool_call_count": len(state["tool_calls"])})
        for tc in state["tool_calls"]:
            tool_exec = runtime.tool_runtime.start_tool(
                tc.get("tool", "unknown"), exec_mcp.id, tc,
            )
            if tc.get("status") == "executed":
                runtime.tool_runtime.complete_tool(tool_exec, tc.get("result", ""))
            elif tc.get("status") == "error":
                runtime.tool_runtime.fail_tool(tool_exec, tc.get("error", ""))
            else:
                runtime.tool_runtime.complete_tool(tool_exec)
    except Exception as e:
        runtime.agent_runtime.fail_agent(exec_mcp, str(e))
    yield _sse_event(runtime, "agent.completed")

    # Emit evidence summary
    if state["evidence"]:
        for ev in state["evidence"][-5:]:
            runtime.emit("evidence.added", {
                "source": ev.get("source", ""),
                "title": ev.get("title", ""),
                "summary": ev.get("summary", ""),
            })
        yield _sse_event(runtime, "evidence.added")

    # --- Diagnosis with streaming LLM ---
    exec_diag = runtime.agent_runtime.start_agent("DiagnosisAgent")
    yield _sse_event(runtime, "agent.started")

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

    state = diagnosis_agent(state, db=None)
    state["llm_reply"] = ""
    runtime.agent_runtime.complete_agent(exec_diag, {"root_causes": state["root_causes"]})

    if state["root_causes"]:
        runtime.emit("diagnosis.updated", {
            "root_causes": state["root_causes"],
            "remediation_plan": state["remediation_plan"],
        })

    # --- Final done event with runtime trace ---
    final = ChatOpsMessageResponse(
        session_id=state["session_id"],
        intent=state["intent"],
        entities=state["entities"],
        reply=_build_reply(
            state["intent"],
            state["entities"],
            state["requires_human_approval"],
            llm_reply="",
            evidence=state["evidence"],
            tool_calls=state["tool_calls"],
        ),
        trace=state["trace"],
        evidence=state["evidence"],
        tool_calls=state["tool_calls"],
        root_causes=state["root_causes"],
        remediation_plan=state["remediation_plan"],
        requires_human_approval=state["requires_human_approval"],
        llm_reply="",
    )
    done_data = final.model_dump()
    done_data["runtime_trace"] = runtime.get_trace()
    yield _sse("done", done_data)
    runtime.cleanup()


def _sse_event(runtime: SessionRuntime, _event_hint: str) -> str:
    """Yield the most recent event from the runtime event bus as SSE."""
    events = runtime.event_bus.events
    if events:
        return events[-1].to_sse()
    return ""


def _build_reply(
    intent: str,
    entities: dict[str, str],
    requires_human_approval: bool,
    llm_reply: str = "",
    evidence: list[dict] | None = None,
    tool_calls: list[dict] | None = None,
) -> str:
    # 优先使用 LLM 生成的自然语言回复
    if llm_reply and llm_reply.strip():
        return llm_reply.strip()

    evidence = evidence or []
    tool_calls = tool_calls or []

    # 从实际工具执行结果中提取可读信息
    namespace = entities.get("namespace") or "默认命名空间"
    workload = entities.get("workload") or "目标对象"

    # 尝试从 evidence 中提取已执行的工具结果
    mcp_evidences = [e for e in evidence if e.get("source") == "mcp" and e.get("score", 0) > 0]
    if mcp_evidences:
        summaries = [e.get("summary", "") for e in mcp_evidences if e.get("summary")]
        if summaries:
            return f"查询 {namespace} 结果:\n" + "\n".join(summaries)

    if intent == "query_cluster":
        return f"已查询 {namespace}，详见工具调用结果。"
    if intent == "query_metric":
        return f"已查询 {namespace} 中 {workload} 的指标数据。"
    if intent == "query_logs":
        return f"已检索 {namespace} 中 {workload} 的日志。"
    if intent == "search_runbook":
        return "已从知识库召回相关处理手册，详见证据列表。"
    if intent == "create_workflow":
        suffix = "该动作需要人工确认。" if requires_human_approval else ""
        return f"已识别为创建排查流程。{suffix}"
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
