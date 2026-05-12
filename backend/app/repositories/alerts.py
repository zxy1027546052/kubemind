from sqlalchemy.orm import Session

from app.models.alerts import Alert


def get_by_id(db: Session, alert_id: int) -> Alert | None:
    return db.query(Alert).filter(Alert.id == alert_id).first()


def list_with_filters(
    db: Session,
    query: str = "",
    severity: str = "",
    status: str = "",
    category: str = "",
    offset: int = 0,
    limit: int = 20,
) -> tuple[int, list[Alert]]:
    q = db.query(Alert)
    if query:
        like = f"%{query}%"
        q = q.filter(Alert.title.like(like) | Alert.description.like(like))
    if severity:
        q = q.filter(Alert.severity == severity)
    if status:
        q = q.filter(Alert.status == status)
    if category:
        q = q.filter(Alert.category == category)
    total = q.count()
    items = q.order_by(Alert.updated_at.desc()).offset(offset).limit(limit).all()
    return total, items


def create(db: Session, alert: Alert) -> Alert:
    db.add(alert)
    db.commit()
    db.refresh(alert)
    return alert


def update(db: Session, alert: Alert) -> Alert:
    db.commit()
    db.refresh(alert)
    return alert


def delete(db: Session, alert: Alert) -> None:
    db.delete(alert)
    db.commit()
