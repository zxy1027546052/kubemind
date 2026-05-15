from app.agents.intent import classify_intent, extract_entities


def test_visible_chinese_log_request_classifies_as_query_logs() -> None:
    message = "查看 default java-demoapp 的错误日志"

    assert classify_intent(message) == "query_logs"
    assert extract_entities(message)["namespace"] == "default"


def test_visible_chinese_event_request_classifies_as_diagnosis() -> None:
    message = "分析 prod payment-api 的事件和异常"

    assert classify_intent(message) == "diagnose_issue"
    assert extract_entities(message)["namespace"] == "prod"
    assert extract_entities(message)["workload"] == "payment-api"


def test_extract_entities_supports_app_workload_names() -> None:
    entities = extract_entities("show default java-demoapp error logs")

    assert entities["namespace"] == "default"
    assert entities["workload"] == "java-demoapp"
