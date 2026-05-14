from fastapi.testclient import TestClient

from app.main import app


def test_chatops_message_returns_intent_trace_and_reply() -> None:
    client = TestClient(app)

    response = client.post(
        "/api/chatops/messages",
        json={
            "session_id": "chat-001",
            "message": "查一下 prod payment-api 的 CPU 指标",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["session_id"] == "chat-001"
    assert body["intent"] == "query_metric"
    assert body["entities"]["namespace"] == "prod"
    assert body["entities"]["workload"] == "payment-api"
    assert body["trace"][0]["agent"] == "PlannerAgent"
    assert body["reply"]


def test_chatops_message_can_query_milvus_vector_data() -> None:
    client = TestClient(app)

    response = client.post(
        "/api/chatops/messages",
        json={
            "session_id": "chat-003",
            "message": "查询 milvus 里面磁盘满的处理手册",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["intent"] == "search_runbook"
    assert any(item["agent"] == "MilvusAgent" for item in body["trace"])
    assert any(call["tool"] == "milvus.vector_search" for call in body["tool_calls"])


def test_chatops_message_can_create_workflow_intent() -> None:
    client = TestClient(app)

    response = client.post(
        "/api/chatops/messages",
        json={
            "session_id": "chat-002",
            "message": "生成排查流程",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["intent"] == "create_workflow"
    assert body["requires_human_approval"] is True


def test_general_chat_intent_not_misclassified() -> None:
    """Conversational messages should not be classified as diagnose_issue."""
    client = TestClient(app)

    for message in ("你是什么模型", "你好", "谢谢", "你能做什么"):
        response = client.post(
            "/api/chatops/messages",
            json={"session_id": "chat-200", "message": message},
        )
        assert response.status_code == 200
        body = response.json()
        assert body["intent"] == "general_chat", f"Message '{message}' got intent={body['intent']}"
        assert body["reply"]


def test_stream_endpoint_returns_sse_events() -> None:
    client = TestClient(app)

    response = client.post(
        "/api/chatops/messages/stream",
        json={
            "session_id": "chat-100",
            "message": "分析 prod payment-api 的错误",
        },
    )

    assert response.status_code == 200
    assert response.headers["content-type"] == "text/event-stream; charset=utf-8"
    body = response.text
    assert "event: agent_done" in body
    assert "event: done" in body
    assert "PlannerAgent" in body
    assert "DiagnosisAgent" in body
