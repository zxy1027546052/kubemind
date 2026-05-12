from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_db
from app.core.schemas import PaginationMeta
from app.schemas.alerts import AlertCreate, AlertPaginatedResponse, AlertResponse, AlertUpdate
from app.services.alerts import (
    create_alert,
    delete_alert,
    get_alert,
    list_alerts,
    replace_alert,
    update_alert,
)

router = APIRouter()


@router.get("", response_model=AlertPaginatedResponse)
def get_alerts(
    query: str = Query(default=""),
    severity: str = Query(default=""),
    status: str = Query(default=""),
    category: str = Query(default=""),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
) -> AlertPaginatedResponse:
    total, items = list_alerts(
        db, query=query, severity=severity, status=status, category=category, offset=offset, limit=limit
    )
    return AlertPaginatedResponse(
        pagination=PaginationMeta(total=total, offset=offset, limit=limit),
        items=[AlertResponse.model_validate(item) for item in items],
    )


@router.post("", response_model=AlertResponse, status_code=status.HTTP_201_CREATED)
def post_alert(payload: AlertCreate, db: Session = Depends(get_db)) -> AlertResponse:
    return AlertResponse.model_validate(create_alert(db, payload))


@router.get("/{alert_id}", response_model=AlertResponse)
def get_one_alert(alert_id: int, db: Session = Depends(get_db)) -> AlertResponse:
    alert = get_alert(db, alert_id)
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    return AlertResponse.model_validate(alert)


@router.put("/{alert_id}", response_model=AlertResponse)
def put_alert(alert_id: int, payload: AlertCreate, db: Session = Depends(get_db)) -> AlertResponse:
    alert = replace_alert(db, alert_id, payload)
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    return AlertResponse.model_validate(alert)


@router.patch("/{alert_id}", response_model=AlertResponse)
def patch_alert(alert_id: int, payload: AlertUpdate, db: Session = Depends(get_db)) -> AlertResponse:
    alert = update_alert(db, alert_id, payload)
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    return AlertResponse.model_validate(alert)


@router.delete("/{alert_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_alert(alert_id: int, db: Session = Depends(get_db)) -> None:
    if not delete_alert(db, alert_id):
        raise HTTPException(status_code=404, detail="Alert not found")
