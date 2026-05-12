from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.api.dependencies import get_db
from app.services.vector_search import SearchResult, search_similar

router = APIRouter()


class SearchResponse(BaseModel):
    query: str
    results: list[SearchResult]
    total: int


@router.get("", response_model=SearchResponse)
def search(
    q: str = Query(default="", description="Search query"),
    type: str = Query(default="all", description="Source types: all, documents, cases, runbooks"),
    top_k: int = Query(default=5, ge=1, le=20),
    db: Session = Depends(get_db),
) -> SearchResponse:
    source_types = None if type == "all" else [t.strip() for t in type.split(",")]
    results = search_similar(db, query=q, source_types=source_types, top_k=top_k)
    return SearchResponse(query=q, results=results, total=len(results))
