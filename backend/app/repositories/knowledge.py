from sqlalchemy.orm import Session

from app.models.knowledge import Document


def get_by_id(db: Session, doc_id: int) -> Document | None:
    return db.query(Document).filter(Document.id == doc_id).first()


def list_with_filters(
    db: Session,
    query: str = "",
    category: str = "",
    offset: int = 0,
    limit: int = 20,
) -> tuple[int, list[Document]]:
    q = db.query(Document)
    if query:
        like = f"%{query}%"
        q = q.filter(
            Document.title.ilike(like)
            | Document.content.ilike(like)
            | Document.category.ilike(like)
        )
    if category:
        q = q.filter(Document.category == category)
    total = q.count()
    items = q.order_by(Document.updated_at.desc()).offset(offset).limit(limit).all()
    return total, items


def create(db: Session, document: Document) -> Document:
    db.add(document)
    db.commit()
    db.refresh(document)
    return document


def update(db: Session, document: Document) -> Document:
    db.commit()
    db.refresh(document)
    return document


def delete(db: Session, document: Document) -> None:
    db.delete(document)
    db.commit()
