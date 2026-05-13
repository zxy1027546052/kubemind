from datetime import datetime, timedelta, timezone

from app.services.anomaly import detect_metric_anomalies


def _point(index: int, value: float) -> dict:
    return {
        "timestamp": datetime(2026, 5, 13, 10, 0, tzinfo=timezone.utc) + timedelta(minutes=index),
        "value": value,
    }


def test_detect_metric_anomalies_flags_current_spike() -> None:
    points = [_point(index, 10.0) for index in range(8)]
    points.append(_point(8, 55.0))

    events = detect_metric_anomalies(
        metric_name="pod_cpu_usage_percent",
        resource_type="pod",
        resource_name="api-7f9d",
        namespace="prod",
        window="15m",
        points=points,
    )

    assert len(events) == 1
    assert events[0]["metric_name"] == "pod_cpu_usage_percent"
    assert events[0]["resource_name"] == "api-7f9d"
    assert events[0]["value"] == 55.0
    assert events[0]["baseline"] == 10.0
    assert events[0]["upper_bound"] == 10.0
    assert events[0]["severity"] == "critical"
    assert events[0]["score"] == 1.0


def test_detect_metric_anomalies_returns_empty_for_normal_series() -> None:
    points = [_point(index, value) for index, value in enumerate([10.0, 11.0, 9.5, 10.5, 10.2, 10.8])]

    events = detect_metric_anomalies(
        metric_name="pod_memory_usage_percent",
        resource_type="pod",
        resource_name="api-7f9d",
        namespace="prod",
        window="15m",
        points=points,
    )

    assert events == []


def test_detect_metric_anomalies_requires_history_before_current_value() -> None:
    points = [_point(0, 10.0), _point(1, 50.0)]

    events = detect_metric_anomalies(
        metric_name="pod_cpu_usage_percent",
        resource_type="pod",
        resource_name="api-7f9d",
        namespace="prod",
        window="15m",
        points=points,
    )

    assert events == []
