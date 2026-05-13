from datetime import datetime, timezone
from statistics import mean, pstdev
from typing import Any

from sqlalchemy.orm import Session

from app.schemas.alerts import AlertCreate
from app.services.alerts import create_alert


def detect_metric_anomalies(
    metric_name: str,
    resource_type: str,
    resource_name: str,
    namespace: str,
    window: str,
    points: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    if len(points) < 3:
        return []

    sorted_points = sorted(points, key=lambda point: point["timestamp"])
    history = sorted_points[:-1]
    current = sorted_points[-1]
    history_values = [float(point["value"]) for point in history]
    current_value = float(current["value"])

    baseline = mean(history_values)
    std = pstdev(history_values)
    upper_bound = baseline + (3 * std)
    lower_bound = baseline - (3 * std)

    if current_value <= upper_bound:
        return []

    score = _calculate_score(current_value=current_value, baseline=baseline, upper_bound=upper_bound)
    severity = _severity_from_score(score)

    return [{
        "metric_name": metric_name,
        "resource_type": resource_type,
        "resource_name": resource_name,
        "namespace": namespace,
        "window": window,
        "value": round(current_value, 4),
        "baseline": round(baseline, 4),
        "upper_bound": round(upper_bound, 4),
        "lower_bound": round(lower_bound, 4),
        "score": score,
        "severity": severity,
        "evidence": [
            f"{metric_name} current value {current_value:.2f} is above dynamic upper bound {upper_bound:.2f}",
        ],
        "detected_at": current.get("timestamp") or datetime.now(timezone.utc),
    }]


def _calculate_score(current_value: float, baseline: float, upper_bound: float) -> float:
    if current_value <= upper_bound:
        return 0.0
    if upper_bound <= baseline:
        return 1.0
    distance = current_value - upper_bound
    scale = max(abs(upper_bound - baseline), 1.0)
    return round(min(1.0, distance / scale), 4)


def _severity_from_score(score: float) -> str:
    if score >= 0.8:
        return "critical"
    if score >= 0.5:
        return "high"
    if score >= 0.25:
        return "medium"
    return "low"


def create_alerts_from_anomalies(db: Session, events: list[dict[str, Any]]) -> list[int]:
    alert_ids: list[int] = []
    for event in events:
        alert = create_alert(
            db,
            AlertCreate(
                title=f"[{event['severity'].title()}] {event['metric_name']} anomaly on {event['resource_name']}",
                description=_build_alert_description(event),
                severity=event["severity"],
                source="anomaly_detector",
                status="active",
                category="anomaly",
            ),
        )
        alert_ids.append(alert.id)
    return alert_ids


def _build_alert_description(event: dict[str, Any]) -> str:
    evidence = "; ".join(event.get("evidence", []))
    return (
        f"Metric {event['metric_name']} on {event['resource_type']} {event['resource_name']} "
        f"in namespace {event.get('namespace', '') or '-'} exceeded dynamic threshold. "
        f"value={event['value']}, baseline={event['baseline']}, upper_bound={event['upper_bound']}. "
        f"{evidence}"
    )
