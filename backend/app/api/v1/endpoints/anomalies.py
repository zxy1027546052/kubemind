from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.dependencies import get_db
from app.schemas.anomaly import AnomalyDetectRequest, AnomalyDetectResponse, AnomalyEvent
from app.services.anomaly import create_alerts_from_anomalies, detect_metric_anomalies

router = APIRouter()


@router.post("/detect", response_model=AnomalyDetectResponse)
def detect_anomalies(
    payload: AnomalyDetectRequest,
    create_alerts: bool = Query(default=False),
    db: Session = Depends(get_db),
) -> AnomalyDetectResponse:
    events = detect_metric_anomalies(
        metric_name=payload.metric_name,
        resource_type=payload.resource_type,
        resource_name=payload.resource_name,
        namespace=payload.namespace,
        window=payload.window,
        points=[point.model_dump() for point in payload.points],
    )
    items = [AnomalyEvent.model_validate(event) for event in events]
    alert_ids = create_alerts_from_anomalies(db, events) if create_alerts and events else []
    return AnomalyDetectResponse(total=len(items), items=items, alert_ids=alert_ids)
