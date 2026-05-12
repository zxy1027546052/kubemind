from datetime import datetime

from sqlalchemy.orm import Session

from app.models.knowledge import Document
from app.repositories import knowledge as repo
from app.schemas.knowledge import DocumentCreate, DocumentUpdate


def list_documents(
    db: Session, query: str = "", category: str = "", offset: int = 0, limit: int = 20
) -> tuple[int, list[Document]]:
    return repo.list_with_filters(db, query=query, category=category, offset=offset, limit=limit)


def get_document(db: Session, document_id: int) -> Document | None:
    return repo.get_by_id(db, document_id)


def create_document(db: Session, payload: DocumentCreate) -> Document:
    now = datetime.now()
    document = Document(**payload.model_dump(), created_at=now, updated_at=now)
    return repo.create(db, document)


def update_document(db: Session, document_id: int, payload: DocumentUpdate) -> Document | None:
    document = repo.get_by_id(db, document_id)
    if not document:
        return None
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(document, key, value)
    document.updated_at = datetime.now()
    return repo.update(db, document)


def replace_document(db: Session, document_id: int, payload: DocumentCreate) -> Document | None:
    document = repo.get_by_id(db, document_id)
    if not document:
        return None
    for key, value in payload.model_dump().items():
        setattr(document, key, value)
    document.updated_at = datetime.now()
    return repo.update(db, document)


def delete_document(db: Session, document_id: int) -> bool:
    document = repo.get_by_id(db, document_id)
    if not document:
        return False
    repo.delete(db, document)
    return True
