from fastapi.testclient import TestClient

from app.main import app


def test_observability_health_endpoint_returns_source_status() -> None:
    client = TestClient(app)

    response = client.get("/api/observability/health")

    assert response.status_code == 200
    assert response.json() == {
        "prometheus": {"enabled": False, "status": "disabled", "message": "PROMETHEUS_BASE_URL is not configured"},
        "loki": {"enabled": False, "status": "disabled", "message": "LOKI_BASE_URL is not configured"},
    }
