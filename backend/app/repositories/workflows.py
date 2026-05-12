from sqlalchemy.orm import Session

from app.models.workflows import Workflow


def get_by_id(db: Session, workflow_id: int) -> Workflow | None:
    return db.query(Workflow).filter(Workflow.id == workflow_id).first()


def list_with_filters(
    db: Session,
    query: str = "",
    category: str = "",
    status: str = "",
    offset: int = 0,
    limit: int = 20,
) -> tuple[int, list[Workflow]]:
    q = db.query(Workflow)
    if query:
        like = f"%{query}%"
        q = q.filter(Workflow.title.like(like) | Workflow.description.like(like))
    if category:
        q = q.filter(Workflow.category == category)
    if status:
        q = q.filter(Workflow.status == status)
    total = q.count()
    items = q.order_by(Workflow.updated_at.desc()).offset(offset).limit(limit).all()
    return total, items


def create(db: Session, workflow: Workflow) -> Workflow:
    db.add(workflow)
    db.commit()
    db.refresh(workflow)
    return workflow


def update(db: Session, workflow: Workflow) -> Workflow:
    db.commit()
    db.refresh(workflow)
    return workflow


def delete(db: Session, workflow: Workflow) -> None:
    db.delete(workflow)
    db.commit()
