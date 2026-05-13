from app.agents.graph import run_ops_graph
from app.agents.state import create_initial_state


def test_run_ops_graph_records_trace_and_root_causes() -> None:
    state = create_initial_state(
        session_id="chat-001",
        user_query="帮我分析 prod payment-api 最近错误日志",
    )

    result = run_ops_graph(state)

    assert result["intent"] == "diagnose_issue"
    assert result["entities"]["namespace"] == "prod"
    assert result["entities"]["workload"] == "payment-api"
    assert [item["agent"] for item in result["trace"]] == [
        "PlannerAgent",
        "RetrieverAgent",
        "MilvusAgent",
        "ObservabilityAgent",
        "DiagnosisAgent",
    ]
    assert result["root_causes"][0]["title"] == "需要进一步排查 payment-api"
    assert result["root_causes"][0]["confidence"] > 0


def test_run_ops_graph_supports_runbook_search_intent() -> None:
    state = create_initial_state(
        session_id="chat-002",
        user_query="找一下磁盘满的处理手册",
    )

    result = run_ops_graph(state)

    assert result["intent"] == "search_runbook"
    assert result["tool_calls"][0]["tool"] == "knowledge.search"
    assert result["evidence"][0]["source"] == "knowledge"


def test_milvus_agent_adds_vector_search_results() -> None:
    from app.agents.nodes import milvus_agent

    state = create_initial_state(
        session_id="chat-003",
        user_query="查询 milvus 里面磁盘满的处理手册",
    )
    state["intent"] = "search_runbook"

    def fake_search(db, query, source_types, top_k):
        return [
            {
                "id": 12,
                "source_type": "runbooks",
                "title": "磁盘空间告警处理手册",
                "score": 0.91,
            }
        ]

    result = milvus_agent(state, db=object(), search_fn=fake_search)

    assert result["tool_calls"][0]["tool"] == "milvus.vector_search"
    assert result["tool_calls"][0]["status"] == "executed"
    assert result["evidence"][0]["source"] == "milvus"
    assert result["evidence"][0]["title"] == "磁盘空间告警处理手册"
    assert result["evidence"][0]["score"] == 0.91
