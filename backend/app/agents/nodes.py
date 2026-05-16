import json
import re
from datetime import datetime, timedelta, timezone
from typing import Any

from app.agents.intent import classify_intent, classify_intents, extract_entities
from app.agents.state import OpsGraphState
from app.services.vector_search import search_similar


def planner_agent(state: OpsGraphState, db=None) -> OpsGraphState:
    intents = classify_intents(state["user_query"], db=db)
    state["intents"] = intents
    state["intent"] = intents[0]
    entities = extract_entities(state["user_query"], db=db, history=state.get("conversation_history"))
    state["entities"].update(entities)
    state["requires_human_approval"] = state["intent"] in {"create_workflow", "scale_recommendation"}
    _append_trace(state, "PlannerAgent", f"intents={intents}, entities={entities}")
    return state


def retriever_agent(state: OpsGraphState) -> OpsGraphState:
    if state["intent"] == "general_chat":
        _append_trace(state, "RetrieverAgent", "general chat, skipped knowledge retrieval")
        return state
    if state["intent"] in {"search_runbook", "diagnose_issue"}:
        query = state["user_query"]
        state["tool_calls"].append({"tool": "knowledge.search", "query": query, "status": "planned"})
        state["evidence"].append({
            "source": "knowledge",
            "title": "相似 Runbook 候选",
            "summary": f"将根据问题检索知识库: {query}",
        })
    _append_trace(state, "RetrieverAgent", "knowledge evidence prepared")
    return state


def milvus_agent(state: OpsGraphState, db=None, search_fn=search_similar) -> OpsGraphState:
    if state["intent"] == "general_chat":
        _append_trace(state, "MilvusAgent", "general chat, skipped vector search")
        return state
    if state["intent"] not in {"search_runbook", "diagnose_issue"}:
        _append_trace(state, "MilvusAgent", "vector search skipped")
        return state

    query = _normalize_vector_query(state["user_query"])
    tool_call = {
        "tool": "milvus.vector_search",
        "query": query,
        "status": "skipped" if db is None else "executed",
    }
    state["tool_calls"].append(tool_call)

    if db is None:
        state["evidence"].append({
            "source": "milvus",
            "title": "Milvus 查询未执行",
            "summary": "当前 Agent 未接收到数据库会话，无法访问向量检索服务。",
            "score": 0.0,
        })
        _append_trace(state, "MilvusAgent", "vector search skipped: db unavailable")
        return state

    results = search_fn(
        db,
        query=query,
        source_types=["documents", "cases", "runbooks"],
        top_k=5,
    )
    if not results:
        state["evidence"].append({
            "source": "milvus",
            "title": "Milvus 未召回结果",
            "summary": f"向量查询未找到匹配内容: {query}",
            "score": 0.0,
        })
        _append_trace(state, "MilvusAgent", "vector search executed: 0 hits")
        return state

    for item in results:
        state["evidence"].append({
            "source": "milvus",
            "title": item.get("title", ""),
            "summary": f"{item.get('source_type', 'unknown')}#{item.get('id', 0)} score={item.get('score', 0)}",
            "score": item.get("score", 0),
            "source_type": item.get("source_type", ""),
            "source_id": item.get("id", 0),
        })
    _append_trace(state, "MilvusAgent", f"vector search executed: {len(results)} hits")
    return state


def observability_agent(state: OpsGraphState) -> OpsGraphState:
    if state["intent"] == "general_chat":
        _append_trace(state, "ObservabilityAgent", "general chat, skipped observability plan")
        return state
    if state["intent"] in {"query_metric", "query_logs", "diagnose_issue", "query_cluster"}:
        workload = state["entities"].get("workload", "")
        namespace = state["entities"].get("namespace", "")
        tool_name = _tool_name_for_intent(state["intent"])
        state["tool_calls"].append({
            "tool": tool_name,
            "namespace": namespace,
            "workload": workload,
            "status": "planned",
        })
        state["evidence"].append({
            "source": "observability",
            "title": "观测数据查询计划",
            "summary": f"准备查询 {namespace or 'default'} / {workload or 'cluster'} 的观测数据",
        })
    _append_trace(state, "ObservabilityAgent", "observability plan prepared")
    return state


def mcp_ops_agent(state: OpsGraphState, db=None, mcp_service=None) -> OpsGraphState:
    if state["intent"] == "general_chat":
        _append_trace(state, "McpOpsAgent", "general chat, skipped MCP tools")
        return state
    if db is None:
        _append_trace(state, "McpOpsAgent", "MCP tools skipped: db unavailable")
        return state

    service = mcp_service or _build_mcp_service()
    requests = _build_mcp_tool_requests(state)
    if not requests:
        _append_trace(state, "McpOpsAgent", "no matching MCP tools")
        return state

    executed = 0
    for request in requests:
        result = service.execute_tool(
            db=db,
            tool_name=request["tool_name"],
            params=request["params"],
            session_id=state["session_id"],
            trace_id=request.get("trace_id"),
            namespace=request.get("namespace", ""),
        )
        status = "executed" if result.get("success") else "error"
        state["tool_calls"].append({
            "tool": request["tool_name"],
            "status": status,
            "namespace": request.get("namespace", ""),
            "workload": state["entities"].get("workload", ""),
            "audit_id": result.get("audit_id"),
            "duration_ms": result.get("duration_ms", 0),
        })
        state["evidence"].append({
            "source": "mcp",
            "title": f"{request['tool_name']} {status}",
            "summary": _structure_tool_result(result, request["tool_name"]),
            "score": 1.0 if result.get("success") else 0.0,
        })
        if result.get("success"):
            executed += 1

    _append_trace(state, "McpOpsAgent", f"MCP tools executed: {executed}/{len(requests)}")
    return state


def diagnosis_agent(state: OpsGraphState, db=None) -> OpsGraphState:
    if state["intent"] == "general_chat":
        state["root_causes"].append({
            "title": "通用对话，非运维诊断请求",
            "confidence": 1.0,
            "evidence_count": 0,
        })
        if db:
            try:
                from app.services.llm import chat_completion
                reply = chat_completion(
                    db,
                    messages=[
                        {"role": "system", "content": "你是 KubeMind 智能运维助手，回答简洁友好。"},
                        {"role": "user", "content": state["user_query"]},
                    ],
                    temperature=0.7,
                    max_tokens=256,
                )
                state["llm_reply"] = reply.strip()
            except Exception:
                state["llm_reply"] = "我是 KubeMind 智能运维助手，请描述你的运维需求。"
        _append_trace(state, "DiagnosisAgent", "general chat reply generated")
        return state

    workload = state["entities"].get("workload") or "当前对象"
    if state["intent"] == "query_metric":
        title = f"已生成 {workload} 指标查询计划"
        confidence = 0.55
    elif state["intent"] == "query_logs":
        title = f"已生成 {workload} 日志查询计划"
        confidence = 0.55
    elif state["intent"] == "search_runbook":
        title = "已生成 Runbook 检索计划"
        confidence = 0.5
    elif state["intent"] == "create_workflow":
        title = "需要人工确认后创建排查流程"
        confidence = 0.6
    else:
        title = f"需要进一步排查 {workload}"
        confidence = 0.65

    state["root_causes"].append({
        "title": title,
        "confidence": confidence,
        "evidence_count": len(state["evidence"]),
    })
    state["remediation_plan"].append({
        "step": "review_evidence",
        "description": "查看工具调用结果和知识库证据后再执行处置动作",
        "requires_human_approval": state["requires_human_approval"],
    })

    if db is not None and state["intent"] in {"diagnose_issue", "search_runbook", "query_metric", "query_logs", "query_cluster"}:
        try:
            from app.services.llm import chat_completion

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
            reply = chat_completion(
                db,
                messages=[
                    {"role": "system", "content": "你是云原生运维专家，回答简洁专业。"},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.3,
                max_tokens=512,
            )
            state["llm_reply"] = reply.strip()
        except Exception:
            state["llm_reply"] = ""

    _append_trace(state, "DiagnosisAgent", "root cause candidates generated")
    return state


def _tool_name_for_intent(intent: str) -> str:
    if intent == "query_logs":
        return "loki.query_range"
    if intent == "query_cluster":
        return "kubernetes.overview"
    return "prometheus.query"


def _build_mcp_service():
    from app.services.mcp import MCPService

    return MCPService()


def _build_mcp_tool_requests(state: OpsGraphState) -> list[dict[str, Any]]:
    intent = state["intent"]
    entities = state["entities"]
    namespace = entities.get("namespace") or "default"
    workload = entities.get("workload") or ""
    metric = entities.get("metric") or "cpu"
    now = datetime.now(timezone.utc)
    start = now - timedelta(minutes=15)

    if intent == "diagnose_issue":
        requests = [
            {"tool_name": "k8s_get_pods", "params": {"namespace": namespace}, "namespace": namespace},
            {
                "tool_name": "k8s_get_events",
                "params": {"namespace": namespace, "involved_object_name": workload, "limit": 50},
                "namespace": namespace,
            },
        ]
        return requests

    if intent == "query_logs":
        return [
            {
                "tool_name": "k8s_get_pod_logs",
                "params": {"namespace": namespace, "name": workload or "unknown", "tail_lines": 100},
                "namespace": namespace,
            },
            {
                "tool_name": "loki_query",
                "params": {
                    "query": _build_loki_query(namespace, workload),
                    "start": start.isoformat(),
                    "end": now.isoformat(),
                    "limit": 100,
                },
                "namespace": namespace,
            },
        ]

    if intent == "query_metric":
        return [{
            "tool_name": "prometheus_query",
            "params": {"query": _build_prometheus_query(namespace, workload, metric)},
            "namespace": namespace,
        }]

    if intent == "query_cluster":
        return [{"tool_name": "k8s_get_pods", "params": {"namespace": namespace}, "namespace": namespace}]

    return []


def _build_prometheus_query(namespace: str, workload: str, metric: str) -> str:
    pod_filter = f',pod=~"{workload}.*"' if workload else ""
    if metric == "memory":
        return f'sum(container_memory_working_set_bytes{{namespace="{namespace}"{pod_filter}}})'
    return f'sum(rate(container_cpu_usage_seconds_total{{namespace="{namespace}"{pod_filter}}}[5m]))'


def _build_loki_query(namespace: str, workload: str) -> str:
    base = f'{{namespace="{namespace}"}}'
    if not workload:
        return base
    return f'{base} |= "{workload}"'


def _summarize_tool_result(result: dict[str, Any]) -> str:
    return _structure_tool_result(result, "")


def _structure_tool_result(result: dict[str, Any], tool_name: str) -> str:
    if not result.get("success"):
        return f"ERROR: {result.get('error') or 'tool execution failed'}"
    payload = result.get("result", {})

    if isinstance(payload, dict):
        if "items" in payload:
            return _format_pod_or_event_list(payload["items"], tool_name)
        if "logs" in payload:
            return _extract_diagnostic_lines(str(payload["logs"]), 3000)
        if "entries" in payload:
            entries = payload["entries"]
            if isinstance(entries, list):
                lines = "\n".join(
                    e.get("line", "") if isinstance(e, dict) else str(e)
                    for e in entries[:100]
                )
                return _extract_diagnostic_lines(lines, 3000)
            return str(entries)[:3000]
        if "query" in payload or "result_type" in payload:
            return json.dumps(payload, ensure_ascii=False, default=str)[:2000]
    if isinstance(payload, list):
        return f"返回 {len(payload)} 条记录:\n" + json.dumps(payload[:20], ensure_ascii=False, default=str)[:3000]
    return json.dumps(payload, ensure_ascii=False, default=str)[:4000]


def _format_pod_or_event_list(items: list, tool_name: str) -> str:
    if not items:
        return "查询结果为空，未找到匹配资源。"

    if tool_name == "k8s_get_events":
        warnings = [i for i in items if i.get("type") == "Warning" or i.get("reason") in ("Failed", "BackOff", "Unhealthy", "OOMKilling", "Evicted")]
        normal_count = len(items) - len(warnings)
        lines = []
        for ev in warnings[:30]:
            reason = ev.get("reason", "")
            msg = ev.get("message", "")
            obj = ev.get("involved_object", ev.get("name", ""))
            lines.append(f"  [Warning] {reason}: {msg} (object={obj})")
        summary = f"共 {len(items)} 个事件 ({len(warnings)} Warning, {normal_count} Normal)"
        if lines:
            summary += ":\n" + "\n".join(lines)
        return summary[:4000]

    non_running = [i for i in items if i.get("status", "").lower() not in ("running", "succeeded")]
    running_count = len(items) - len(non_running)
    lines = []
    for pod in non_running[:30]:
        name = pod.get("name", "-")
        ns = pod.get("namespace", "")
        status = pod.get("status", "")
        restarts = pod.get("restarts", pod.get("restart_count", ""))
        node = pod.get("node", "")
        line = f"  - {name} [{status}]"
        if ns:
            line += f" ns={ns}"
        if restarts:
            line += f" restarts={restarts}"
        if node:
            line += f" node={node}"
        lines.append(line)
    summary = f"共 {len(items)} 个 Pod ({running_count} Running, {len(non_running)} 异常)"
    if lines:
        summary += ":\n" + "\n".join(lines)
    return summary[:4000]


_DIAGNOSTIC_PATTERNS = re.compile(
    r"(error|exception|panic|oom|timeout|fatal|crash|kill|fail|refused|unavailable|backoff)",
    re.IGNORECASE,
)


def _extract_diagnostic_lines(text: str, max_chars: int) -> str:
    lines = text.split("\n")
    diagnostic_lines: list[str] = []
    for i, line in enumerate(lines):
        if _DIAGNOSTIC_PATTERNS.search(line):
            start = max(0, i - 1)
            end = min(len(lines), i + 2)
            for j in range(start, end):
                if lines[j] not in diagnostic_lines:
                    diagnostic_lines.append(lines[j])
    if diagnostic_lines:
        result = f"[诊断相关行 {len(diagnostic_lines)}/{len(lines)} 总行]:\n" + "\n".join(diagnostic_lines)
        return result[:max_chars]
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + f"\n... (截断，共 {len(lines)} 行)"


def _normalize_vector_query(query: str) -> str:
    return (
        query.replace("milvus", "")
        .replace("Milvus", "")
        .replace("向量数据库", "")
        .replace("向量库", "")
        .replace("里面", "")
        .replace("查询", "")
        .strip()
        or query
    )


def _append_trace(state: OpsGraphState, agent: str, message: str) -> None:
    state["trace"].append({"agent": agent, "message": message})
