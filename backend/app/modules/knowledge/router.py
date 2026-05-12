from fastapi import APIRouter, HTTPException, Query, status

from app.core.schemas import Document, DocumentCreate, DocumentListResponse
from app.modules.knowledge.store import create_document, delete_document, list_documents

router = APIRouter(prefix="/api/documents", tags=["documents"])


@router.get("", response_model=DocumentListResponse)
def get_documents(
    query: str = Query(default=""),
    category: str = Query(default=""),
) -> DocumentListResponse:
    items = list_documents(query=query, category=category)
    return DocumentListResponse(total=len(items), items=items)


@router.post("", response_model=Document, status_code=status.HTTP_201_CREATED)
def post_document(payload: DocumentCreate) -> Document:
    return create_document(payload)


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_document(document_id: int) -> None:
    deleted = delete_document(document_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Document not found")
