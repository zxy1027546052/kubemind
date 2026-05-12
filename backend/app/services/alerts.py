from datetime import datetime

from sqlalchemy.orm import Session

from app.models.alerts import Alert
from app.repositories import alerts as repo
from app.schemas.alerts import AlertCreate, AlertUpdate


def list_alerts(
    db: Session,
    query: str = "",
    severity: str = "",
    status: str = "",
    category: str = "",
    offset: int = 0,
    limit: int = 20,
) -> tuple[int, list[Alert]]:
    return repo.list_with_filters(
        db, query=query, severity=severity, status=status, category=category, offset=offset, limit=limit
    )


def get_alert(db: Session, alert_id: int) -> Alert | None:
    return repo.get_by_id(db, alert_id)


def create_alert(db: Session, payload: AlertCreate) -> Alert:
    now = datetime.now()
    alert = Alert(**payload.model_dump(), created_at=now, updated_at=now)
    return repo.create(db, alert)


def update_alert(db: Session, alert_id: int, payload: AlertUpdate) -> Alert | None:
    alert = repo.get_by_id(db, alert_id)
    if not alert:
        return None
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(alert, key, value)
    alert.updated_at = datetime.now()
    return repo.update(db, alert)


def replace_alert(db: Session, alert_id: int, payload: AlertCreate) -> Alert | None:
    alert = repo.get_by_id(db, alert_id)
    if not alert:
        return None
    for key, value in payload.model_dump().items():
        setattr(alert, key, value)
    alert.updated_at = datetime.now()
    return repo.update(db, alert)


def delete_alert(db: Session, alert_id: int) -> bool:
    alert = repo.get_by_id(db, alert_id)
    if not alert:
        return False
    repo.delete(db, alert)
    return True
