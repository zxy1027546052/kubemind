from app.agents.state import create_initial_state


def test_mcp_ops_agent_executes_read_only_tools_for_diagnosis() -> None:
    from app.agents.nodes import mcp_ops_agent

    state = create_initial_state(
        session_id="chat-004",
        user_query="分析 prod payment-api 为什么异常",
    )
    state["intent"] = "diagnose_issue"
    state["entities"] = {"namespace": "prod", "workload": "payment-api"}
    calls: list[dict] = []

    class FakeMCPService:
        def execute_tool(self, **kwargs):
            calls.append(kwargs)
            return {
                "success": True,
                "result": {"items": [{"name": "payment-api-1", "reason": "BackOff"}]},
                "duration_ms": 3,
                "audit_id": 99,
            }

    result = mcp_ops_agent(state, db=object(), mcp_service=FakeMCPService())

    assert [call["tool_name"] for call in calls] == ["k8s_get_pods", "k8s_get_events"]
    assert all(call["namespace"] == "prod" for call in calls)
    assert any(item["agent"] == "McpOpsAgent" for item in result["trace"])
    assert any(call["tool"] == "k8s_get_events" and call["status"] == "executed" for call in result["tool_calls"])
    assert any(evidence["source"] == "mcp" and "k8s_get_events" in evidence["title"] for evidence in result["evidence"])


def test_mcp_ops_agent_executes_log_tools_for_log_query() -> None:
    from app.agents.nodes import mcp_ops_agent

    state = create_initial_state(
        session_id="chat-005",
        user_query="查看 prod payment-api 的错误日志",
    )
    state["intent"] = "query_logs"
    state["entities"] = {"namespace": "prod", "workload": "payment-api"}
    calls: list[dict] = []

    class FakeMCPService:
        def execute_tool(self, **kwargs):
            calls.append(kwargs)
            return {
                "success": True,
                "result": {"logs": "connection timeout", "entries": [{"line": "error"}]},
                "duration_ms": 5,
                "audit_id": 100,
            }

    result = mcp_ops_agent(state, db=object(), mcp_service=FakeMCPService())

    assert [call["tool_name"] for call in calls] == ["k8s_get_pod_logs", "loki_query"]
    assert calls[0]["params"]["name"] == "payment-api"
    assert any(call["tool"] == "loki_query" and call["status"] == "executed" for call in result["tool_calls"])
    assert any(evidence["source"] == "mcp" and "connection timeout" in evidence["summary"] for evidence in result["evidence"])
