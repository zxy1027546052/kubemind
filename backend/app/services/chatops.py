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
    
    if intent == "query_cluster":
        return _format_cluster_response(namespace, workload, mcp_evidences, tool_calls)
    if intent == "query_metric":
        return _format_metric_response(namespace, workload, mcp_evidences)
    if intent == "query_logs":
        return _format_logs_response(namespace, workload, mcp_evidences)
    if intent == "search_runbook":
        return _format_runbook_response(evidence)
    if intent == "create_workflow":
        suffix = "该动作需要人工确认。" if requires_human_approval else ""
        return f"已识别为创建排查流程。{suffix}"
    if intent == "diagnose_issue":
        return _format_diagnosis_response(namespace, workload, evidence, tool_calls)
    if intent == "general_chat":
        return (
            "我是 KubeMind 智能运维助手，支持以下能力：\n\n"
            "📊 **指标查询** — 查询 CPU、内存等资源指标\n"
            "📝 **日志查询** — 检索服务错误日志\n"
            "🔍 **故障诊断** — 分析故障现象并生成根因候选\n"
            "📚 **Runbook 检索** — 从知识库召回相关处理手册\n"
            "☸️ **集群查询** — 查看集群、节点、Pod 状态\n"
            "🔄 **流程创建** — 生成标准化排查流程\n\n"
            "请用自然语言描述你的运维需求。"
        )
    return f"已识别为故障诊断，将围绕 `{namespace}` 中 `{workload}` 收集证据并生成根因候选。"


def _format_cluster_response(namespace: str, workload: str, evidences: list, tool_calls: list) -> str:
    """格式化集群查询响应"""
    result = [f"## 查询结果: `{namespace}` 命名空间"]
    
    if evidences:
        for ev in evidences[:3]:
            summary = ev.get("summary", "")
            if summary:
                try:
                    data = json.loads(summary)
                    if isinstance(data, dict) and "items" in data:
                        items = data["items"]
                        if isinstance(items, list) and len(items) > 0:
                            result.append(f"\n### 发现 {len(items)} 个对象")
                            for item in items[:5]:
                                name = item.get("name", item.get("metadata", {}).get("name", "Unknown"))
                                status = item.get("status", item.get("phase", "Unknown"))
                                result.append(f"- `{name}` | {status}")
                            if len(items) > 5:
                                result.append(f"- ... 还有 {len(items) - 5} 个")
                        else:
                            result.append(f"\n{summary[:300]}")
                    else:
                        result.append(f"\n{summary[:300]}")
                except:
                    result.append(f"\n{summary[:300]}")
    
    if tool_calls:
        result.append("\n### 执行的工具")
        for tc in tool_calls:
            status = "✅" if tc.get("status") == "executed" else "❌"
            result.append(f"{status} `{tc.get('tool', '')}`")
    
    return "\n".join(result)


def _format_metric_response(namespace: str, workload: str, evidences: list) -> str:
    """格式化指标查询响应"""
    result = [f"## 指标查询: `{namespace}` / `{workload}`"]
    
    if evidences:
        for ev in evidences[:2]:
            summary = ev.get("summary", "")
            if summary:
                try:
                    data = json.loads(summary)
                    if isinstance(data, dict):
                        result.append("\n### 指标数据")
                        for key, value in list(data.items())[:6]:
                            if isinstance(value, dict) and "value" in value:
                                val = value["value"]
                                result.append(f"- **{key}**: `{val}`")
                            elif isinstance(value, (int, float)):
                                result.append(f"- **{key}**: `{value}`")
                            else:
                                result.append(f"- **{key}**: {str(value)[:50]}")
                    else:
                        result.append(f"\n{summary[:400]}")
                except:
                    result.append(f"\n{summary[:400]}")
    
    return "\n".join(result)


def _format_logs_response(namespace: str, workload: str, evidences: list) -> str:
    """格式化日志查询响应"""
    result = [f"## 日志查询: `{namespace}` / `{workload}`"]
    
    if evidences:
        for ev in evidences[:2]:
            summary = ev.get("summary", "")
            if summary:
                try:
                    data = json.loads(summary)
                    if isinstance(data, dict) and "result" in data:
                        logs = data["result"]
                        if isinstance(logs, list):
                            result.append("\n### 日志片段")
                            for log_entry in logs[:8]:
                                if isinstance(log_entry, dict):
                                    ts = log_entry.get("timestamp", log_entry.get("ts", ""))
                                    msg = log_entry.get("message", log_entry.get("line", ""))
                                    result.append(f"`{ts}` | {msg[:80]}")
                                elif isinstance(log_entry, str):
                                    result.append(log_entry[:100])
                        else:
                            result.append(f"\n{summary[:400]}")
                    else:
                        result.append(f"\n{summary[:400]}")
                except:
                    result.append(f"\n{summary[:400]}")
    
    return "\n".join(result)


def _format_runbook_response(evidence: list) -> str:
    """格式化 Runbook 检索响应"""
    result = ["## 知识库检索结果"]
    
    kb_evidence = [e for e in evidence if e.get("source") == "milvus"]
    if kb_evidence:
        result.append(f"\n### 找到 {len(kb_evidence)} 个相关文档")
        for i, ev in enumerate(kb_evidence[:3], 1):
            title = ev.get("title", "Untitled")
            score = ev.get("score", 0)
            summary = ev.get("summary", "")
            result.append(f"\n{i}. **{title}**")
            result.append(f"   匹配度: {int(score * 100)}%")
            result.append(f"   {summary[:150]}...")
    else:
        result.append("\n未找到相关文档")
    
    return "\n".join(result)


def _format_diagnosis_response(namespace: str, workload: str, evidence: list, tool_calls: list) -> str:
    """格式化诊断响应"""
    result = [f"## 故障诊断分析"]
    result.append(f"\n**目标**: `{namespace}` / `{workload}`")
    
    # 执行的工具
    if tool_calls:
        executed = [tc for tc in tool_calls if tc.get("status") == "executed"]
        result.append(f"\n**已收集证据**: {len(executed)}/{len(tool_calls)} 工具执行成功")
    
    # 证据摘要
    mcp_evidence = [e for e in evidence if e.get("source") == "mcp"]
    if mcp_evidence:
        result.append("\n**证据来源**:")
        for ev in mcp_evidence[:3]:
            result.append(f"- `{ev.get('title', '')}`")
    
    return "\n".join(result)


def _sse(event: str, data: dict | str) -> str:
    payload = json.dumps(data, ensure_ascii=False)
    return f"event: {event}\ndata: {payload}\n\n"
