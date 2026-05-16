import json
from collections.abc import Generator

from sqlalchemy.orm import Session

from app.agents.graph import run_ops_graph_with_db
from app.agents.memory import conversation_memory
from app.agents.state import create_initial_state
from app.runtime import SessionRuntime
from app.schemas.chatops import ChatOpsMessageRequest, ChatOpsMessageResponse


def handle_chatops_message(payload: ChatOpsMessageRequest, db: Session | None = None) -> ChatOpsMessageResponse:
    history = conversation_memory.get_history(payload.session_id or "")
    state = create_initial_state(session_id=payload.session_id, user_query=payload.message, history=history)
    result = run_ops_graph_with_db(state, db=db)
    response = ChatOpsMessageResponse(
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
    sid = result["session_id"]
    conversation_memory.add_message(sid, "user", payload.message)
    conversation_memory.add_message(sid, "assistant", response.reply or response.llm_reply)
    return response


def handle_chatops_message_stream(
    payload: ChatOpsMessageRequest, db: Session | None = None
) -> Generator[str, None, None]:
    """Run the agent graph and yield structured SSE events via Runtime Layer."""
    from app.agents.nodes import diagnosis_agent, planner_agent
    from app.agents.react import ReactExecutor
    from app.services.llm import chat_completion_stream

    state = create_initial_state(
        session_id=payload.session_id,
        user_query=payload.message,
        history=conversation_memory.get_history(payload.session_id or ""),
    )
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

    # --- ReAct or General Chat ---
    if db and state["intent"] != "general_chat":
        exec_react = runtime.agent_runtime.start_agent("ReactExecutor")
        yield _sse_event(runtime, "agent.started")
        try:
            executor = ReactExecutor(db=db, state=state)
            for sse_event in executor.run_stream():
                yield sse_event
            state = executor.state
            runtime.agent_runtime.complete_agent(exec_react, {
                "tool_call_count": len(state["tool_calls"]),
                "evidence_count": len(state["evidence"]),
            })
        except Exception as e:
            runtime.agent_runtime.fail_agent(exec_react, str(e))
        yield _sse_event(runtime, "agent.completed")

        # Emit evidence summary
        if state["evidence"]:
            for ev in state["evidence"][-5:]:
                runtime.emit("evidence.added", {
                    "source": ev.get("source", ""),
                    "title": ev.get("title", ""),
                    "summary": ev.get("summary", "")[:200],
                })
            yield _sse_event(runtime, "evidence.added")

        # Stream the final answer if ReAct produced one
        if state.get("llm_reply"):
            for chunk in state["llm_reply"]:
                yield _sse("token", {"content": chunk})
    else:
        # General chat: stream LLM reply directly
        exec_diag = runtime.agent_runtime.start_agent("DiagnosisAgent")
        yield _sse_event(runtime, "agent.started")
        if db:
            try:
                for token in chat_completion_stream(
                    db,
                    messages=[
                        {"role": "system", "content": "你是 KubeMind 智能运维助手，回答简洁友好。"},
                        {"role": "user", "content": state["user_query"]},
                    ],
                    temperature=0.7,
                    max_tokens=256,
                ):
                    yield _sse("token", {"content": token})
                    state["llm_reply"] = state.get("llm_reply", "") + token
            except Exception:
                yield _sse("token", {"content": "[LLM 服务暂不可用]"})
        state = diagnosis_agent(state, db=None)
        runtime.agent_runtime.complete_agent(exec_diag, {"root_causes": state["root_causes"]})

    if state["root_causes"]:
        runtime.emit("diagnosis.updated", {
            "root_causes": state["root_causes"],
            "remediation_plan": state["remediation_plan"],
        })

    # --- Final done event with runtime trace ---
    conversation_memory.add_message(state["session_id"], "user", payload.message)
    conversation_memory.add_message(state["session_id"], "assistant", state.get("llm_reply", ""))
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
