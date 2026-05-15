from datetime import datetime, timezone

from app.services.ops_tools import build_ops_tool_registry


class FakeK8sClient:
    def get_pods(self, namespace: str = "") -> list[dict]:
        return [{"name": "api-1", "namespace": namespace or "default", "status": "Running"}]

    def get_events(self, namespace: str = "", involved_object_name: str = "", limit: int = 50) -> list[dict]:
        return [{"namespace": namespace or "default", "reason": "BackOff", "message": involved_object_name}]

    def get_pod_logs(self, name: str, namespace: str = "default", tail_lines: int = 100) -> dict:
        return {"name": name, "namespace": namespace, "tail_lines": tail_lines, "logs": "ready"}

    def describe_pod(self, name: str, namespace: str = "default") -> dict:
        return {"name": name, "namespace": namespace, "status": "Running", "containers": []}


class FakeObservabilityClient:
    def query_prometheus(self, query: str):
        return type("Result", (), {"query": query, "result_type": "vector", "points": []})()

    def query_prometheus_range(self, query: str, start: datetime, end: datetime, step: str):
        return type("Result", (), {"query": query, "result_type": "matrix", "points": []})()

    def query_loki_range(self, query: str, start: datetime, end: datetime, limit: int):
        return type("Result", (), {"query": query, "entries": [{"line": "timeout"}]})()


def test_ops_tool_registry_exposes_read_only_tool_specs() -> None:
    registry = build_ops_tool_registry(
        k8s_client_factory=FakeK8sClient,
        observability_client_factory=FakeObservabilityClient,
    )

    assert set(registry) >= {
        "k8s_get_pods",
        "k8s_get_events",
        "k8s_get_pod_logs",
        "k8s_describe_pod",
        "prometheus_query",
        "prometheus_range_query",
        "loki_query",
    }
    assert all(spec.risk_level in {"low", "medium"} for spec in registry.values())
    assert all(spec.is_read_only for spec in registry.values())


def test_ops_tool_registry_executes_prometheus_and_loki_wrappers() -> None:
    registry = build_ops_tool_registry(
        k8s_client_factory=FakeK8sClient,
        observability_client_factory=FakeObservabilityClient,
    )

    instant = registry["prometheus_query"].handler(query="up")
    ranged = registry["prometheus_range_query"].handler(
        query="rate(http_requests_total[5m])",
        start="2026-05-16T00:00:00+00:00",
        end="2026-05-16T00:05:00+00:00",
        step="30s",
    )
    logs = registry["loki_query"].handler(
        query='{namespace="prod"}',
        start=datetime(2026, 5, 16, tzinfo=timezone.utc),
        end=datetime(2026, 5, 16, 0, 5, tzinfo=timezone.utc),
        limit=10,
    )

    assert instant == {"query": "up", "result_type": "vector", "points": []}
    assert ranged["result_type"] == "matrix"
    assert logs["entries"] == [{"line": "timeout"}]


def test_ops_tool_registry_executes_kubernetes_read_only_wrappers() -> None:
    registry = build_ops_tool_registry(
        k8s_client_factory=FakeK8sClient,
        observability_client_factory=FakeObservabilityClient,
    )

    assert registry["k8s_get_pods"].handler(namespace="prod")["items"][0]["namespace"] == "prod"
    assert registry["k8s_get_events"].handler(namespace="prod", involved_object_name="api-1")["items"][0]["reason"] == "BackOff"
    assert registry["k8s_get_pod_logs"].handler(namespace="prod", name="api-1", tail_lines=20)["logs"] == "ready"
    assert registry["k8s_describe_pod"].handler(namespace="prod", name="api-1")["status"] == "Running"
