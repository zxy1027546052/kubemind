from sqlalchemy.orm import Session

from app.models.runbooks import Runbook


def get_by_id(db: Session, runbook_id: int) -> Runbook | None:
    return db.query(Runbook).filter(Runbook.id == runbook_id).first()


def list_with_filters(
    db: Session,
    query: str = "",
    category: str = "",
    offset: int = 0,
    limit: int = 20,
) -> tuple[int, list[Runbook]]:
    q = db.query(Runbook)
    if query:
        like = f"%{query}%"
        q = q.filter(
            Runbook.title.ilike(like)
            | Runbook.scenario.ilike(like)
            | Runbook.steps.ilike(like)
        )
    if category:
        q = q.filter(Runbook.category == category)
    total = q.count()
    items = q.order_by(Runbook.updated_at.desc()).offset(offset).limit(limit).all()
    return total, items


def create(db: Session, runbook: Runbook) -> Runbook:
    db.add(runbook)
    db.commit()
    db.refresh(runbook)
    return runbook


def update(db: Session, runbook: Runbook) -> Runbook:
    db.commit()
    db.refresh(runbook)
    return runbook


def delete(db: Session, runbook: Runbook) -> None:
    db.delete(runbook)
    db.commit()
