from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from app.api.dependencies import get_db
from app.main import app
from app.models.alerts import Alert


def test_detect_anomalies_endpoint_returns_detected_events() -> None:
    client = TestClient(app)
    start = datetime(2026, 5, 13, 10, 0, tzinfo=timezone.utc)

    response = client.post(
        "/api/anomalies/detect",
        json={
            "metric_name": "pod_cpu_usage_percent",
            "resource_type": "pod",
            "resource_name": "api-7f9d",
            "namespace": "prod",
            "window": "15m",
            "points": [
                {"timestamp": (start + timedelta(minutes=index)).isoformat(), "value": 10.0}
                for index in range(8)
            ]
            + [{"timestamp": (start + timedelta(minutes=8)).isoformat(), "value": 55.0}],
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["metric_name"] == "pod_cpu_usage_percent"
    assert body["items"][0]["severity"] == "critical"


def test_detect_anomalies_endpoint_can_create_alerts() -> None:
    class FakeDb:
        def __init__(self) -> None:
            self.alerts = []

        def add(self, alert: Alert) -> None:
            alert.id = len(self.alerts) + 1
            self.alerts.append(alert)

        def commit(self) -> None:
            pass

        def refresh(self, alert: Alert) -> None:
            pass

    fake_db = FakeDb()

    def override_get_db():
        yield fake_db

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)
    start = datetime(2026, 5, 13, 10, 0, tzinfo=timezone.utc)

    try:
        response = client.post(
            "/api/anomalies/detect?create_alerts=true",
            json={
                "metric_name": "pod_cpu_usage_percent",
                "resource_type": "pod",
                "resource_name": "api-7f9d",
                "namespace": "prod",
                "window": "15m",
                "points": [
                    {"timestamp": (start + timedelta(minutes=index)).isoformat(), "value": 10.0}
                    for index in range(8)
                ]
                + [{"timestamp": (start + timedelta(minutes=8)).isoformat(), "value": 55.0}],
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["alert_ids"] == [1]
    assert len(fake_db.alerts) == 1
    assert fake_db.alerts[0].source == "anomaly_detector"
    assert fake_db.alerts[0].category == "anomaly"
