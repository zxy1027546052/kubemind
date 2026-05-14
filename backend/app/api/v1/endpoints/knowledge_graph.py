from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.dependencies import get_db
from app.schemas.knowledge_graph import (
    GraphBuildRequest,
    GraphBuildResponse,
    GraphResponse,
)
from app.services.knowledge_graph import get_graph_snapshot, rebuild_graph

router = APIRouter()


@router.get("/graph", response_model=GraphResponse)
def get_graph(
    entity_type: str | None = Query(None, description="Filter by entity type"),
    limit: int = Query(500, ge=1, le=2000),
    db: Session = Depends(get_db),
) -> dict:
    """Retrieve the full knowledge graph snapshot for visualization."""
    return get_graph_snapshot(db, entity_type=entity_type, limit=limit)


@router.post("/graph/build", response_model=GraphBuildResponse)
def build_graph(body: GraphBuildRequest, db: Session = Depends(get_db)) -> dict:
    """Trigger a rebuild of the knowledge graph from external sources."""
    return rebuild_graph(db, source=body.source)
