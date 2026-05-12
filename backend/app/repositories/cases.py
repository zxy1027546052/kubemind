from sqlalchemy.orm import Session

from app.models.cases import Case


def get_by_id(db: Session, case_id: int) -> Case | None:
    return db.query(Case).filter(Case.id == case_id).first()


def list_with_filters(
    db: Session,
    query: str = "",
    category: str = "",
    severity: str = "",
    status: str = "",
    offset: int = 0,
    limit: int = 20,
) -> tuple[int, list[Case]]:
    q = db.query(Case)
    if query:
        like = f"%{query}%"
        q = q.filter(
            Case.title.ilike(like)
            | Case.symptom.ilike(like)
            | Case.root_cause.ilike(like)
        )
    if category:
        q = q.filter(Case.category == category)
    if severity:
        q = q.filter(Case.severity == severity)
    if status:
        q = q.filter(Case.status == status)
    total = q.count()
    items = q.order_by(Case.updated_at.desc()).offset(offset).limit(limit).all()
    return total, items


def create(db: Session, case: Case) -> Case:
    db.add(case)
    db.commit()
    db.refresh(case)
    return case


def update(db: Session, case: Case) -> Case:
    db.commit()
    db.refresh(case)
    return case


def delete(db: Session, case: Case) -> None:
    db.delete(case)
    db.commit()
