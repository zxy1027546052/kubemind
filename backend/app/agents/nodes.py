from app.agents.intent import classify_intent, extract_entities
from app.agents.state import OpsGraphState
from app.services.vector_search import search_similar


def planner_agent(state: OpsGraphState, db=None) -> OpsGraphState:
    intent = classify_intent(state["user_query"], db=db)
    entities = extract_entities(state["user_query"])
    state["intent"] = intent
    state["entities"].update(entities)
    state["requires_human_approval"] = intent in {"create_workflow", "scale_recommendation"}
    _append_trace(state, "PlannerAgent", f"intent={intent}")
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

    if db is not None and state["intent"] in {"diagnose_issue", "search_runbook", "query_metric", "query_logs"}:
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
