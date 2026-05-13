from datetime import datetime, timezone

from app.services.observability import (
    ObservabilityClient,
    PrometheusQueryResult,
    build_loki_entries,
    build_prometheus_points,
)


def test_build_prometheus_points_normalizes_matrix_values() -> None:
    payload = {
        "status": "success",
        "data": {
            "resultType": "matrix",
            "result": [
                {
                    "metric": {"pod": "api-1", "namespace": "prod"},
                    "values": [[1715580000, "0.42"], [1715580060, "0.55"]],
                }
            ],
        },
    }

    points = build_prometheus_points(payload)

    assert points == [
        {
            "metric": {"pod": "api-1", "namespace": "prod"},
            "timestamp": datetime.fromtimestamp(1715580000, tz=timezone.utc),
            "value": 0.42,
        },
        {
            "metric": {"pod": "api-1", "namespace": "prod"},
            "timestamp": datetime.fromtimestamp(1715580060, tz=timezone.utc),
            "value": 0.55,
        },
    ]


def test_build_loki_entries_normalizes_stream_values() -> None:
    payload = {
        "status": "success",
        "data": {
            "result": [
                {
                    "stream": {"app": "payment-api", "namespace": "prod"},
                    "values": [
                        ["1715580000000000000", "connection timeout"],
                        ["1715580060000000000", "retry failed"],
                    ],
                }
            ],
        },
    }

    entries = build_loki_entries(payload)

    assert entries == [
        {
            "labels": {"app": "payment-api", "namespace": "prod"},
            "timestamp": datetime.fromtimestamp(1715580000, tz=timezone.utc),
            "line": "connection timeout",
        },
        {
            "labels": {"app": "payment-api", "namespace": "prod"},
            "timestamp": datetime.fromtimestamp(1715580060, tz=timezone.utc),
            "line": "retry failed",
        },
    ]


def test_client_reports_disabled_sources_without_base_urls() -> None:
    client = ObservabilityClient(prometheus_base_url="", loki_base_url="")

    health = client.health()

    assert health.prometheus.enabled is False
    assert health.prometheus.status == "disabled"
    assert health.loki.enabled is False
    assert health.loki.status == "disabled"


def test_prometheus_query_result_preserves_query_and_points() -> None:
    points = [
        {
            "metric": {"instance": "node-1"},
            "timestamp": datetime.fromtimestamp(1715580000, tz=timezone.utc),
            "value": 1.5,
        }
    ]

    result = PrometheusQueryResult(query="up", result_type="vector", points=points)

    assert result.query == "up"
    assert result.result_type == "vector"
    assert result.points == points
