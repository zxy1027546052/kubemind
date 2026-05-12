from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_db
from app.core.schemas import PaginationMeta
from app.schemas.knowledge import (
    DocumentCreate,
    DocumentPaginatedResponse,
    DocumentResponse,
    DocumentUpdate,
)
from app.services.knowledge import (
    create_document,
    delete_document,
    get_document,
    list_documents,
    replace_document,
    update_document,
)

router = APIRouter()


@router.get("", response_model=DocumentPaginatedResponse)
def get_documents(
    query: str = Query(default=""),
    category: str = Query(default=""),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
) -> DocumentPaginatedResponse:
    total, items = list_documents(db, query=query, category=category, offset=offset, limit=limit)
    return DocumentPaginatedResponse(
        pagination=PaginationMeta(total=total, offset=offset, limit=limit),
        items=[DocumentResponse.model_validate(item) for item in items],
    )


@router.post("", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
def post_document(payload: DocumentCreate, db: Session = Depends(get_db)) -> DocumentResponse:
    return DocumentResponse.model_validate(create_document(db, payload))


@router.get("/{document_id}", response_model=DocumentResponse)
def get_one_document(document_id: int, db: Session = Depends(get_db)) -> DocumentResponse:
    doc = get_document(db, document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return DocumentResponse.model_validate(doc)


@router.put("/{document_id}", response_model=DocumentResponse)
def put_document(document_id: int, payload: DocumentCreate, db: Session = Depends(get_db)) -> DocumentResponse:
    doc = replace_document(db, document_id, payload)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return DocumentResponse.model_validate(doc)


@router.patch("/{document_id}", response_model=DocumentResponse)
def patch_document(document_id: int, payload: DocumentUpdate, db: Session = Depends(get_db)) -> DocumentResponse:
    doc = update_document(db, document_id, payload)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return DocumentResponse.model_validate(doc)


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_document(document_id: int, db: Session = Depends(get_db)) -> None:
    if not delete_document(db, document_id):
        raise HTTPException(status_code=404, detail="Document not found")
