from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from app.core.schemas import PaginatedResponse


# --- Entity ---

class KnowledgeEntityBase(BaseModel):
    label: str = Field(min_length=1, max_length=200)
    entity_type: str = Field(min_length=1, max_length=50)
    external_id: Optional[str] = Field(default=None, max_length=200)
    properties: str = Field(default="{}", max_length=10000)


class KnowledgeEntityCreate(KnowledgeEntityBase):
    pass


class KnowledgeEntityUpdate(BaseModel):
    label: Optional[str] = Field(default=None, min_length=1, max_length=200)
    properties: Optional[str] = Field(default=None, max_length=10000)


class KnowledgeEntityResponse(KnowledgeEntityBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class KnowledgeEntityPaginatedResponse(PaginatedResponse[KnowledgeEntityResponse]):
    pass


# --- Relationship ---

class KnowledgeRelationshipBase(BaseModel):
    source_id: int
    target_id: int
    relation_type: str = Field(min_length=1, max_length=50)
    weight: float = Field(default=1.0, ge=0.0, le=1.0)
    properties: str = Field(default="{}", max_length=5000)


class KnowledgeRelationshipCreate(KnowledgeRelationshipBase):
    pass


class KnowledgeRelationshipUpdate(BaseModel):
    weight: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    properties: Optional[str] = Field(default=None, max_length=5000)


class KnowledgeRelationshipResponse(KnowledgeRelationshipBase):
    id: int
    created_at: datetime

    model_config = {"from_attributes": True}


class KnowledgeRelationshipPaginatedResponse(PaginatedResponse[KnowledgeRelationshipResponse]):
    pass


# --- Graph view ---

class GraphNode(BaseModel):
    """Frontend-facing graph node for visualization."""
    id: int
    label: str
    entity_type: str
    external_id: Optional[str] = None
    properties: str = "{}"


class GraphEdge(BaseModel):
    """Frontend-facing graph edge for visualization."""
    id: int
    source: int
    target: int
    relation_type: str
    weight: float = 1.0


class GraphResponse(BaseModel):
    """Complete graph snapshot for frontend rendering."""
    nodes: list[GraphNode] = []
    edges: list[GraphEdge] = []


# --- Build request ---

class GraphBuildRequest(BaseModel):
    """Trigger a rebuild of the knowledge graph from external sources."""
    source: str = Field(default="all", pattern="^(k8s|runbooks|cases|all)$")
    """Which source to rebuild from: k8s / runbooks / cases / all"""


class GraphBuildResponse(BaseModel):
    message: str
    entities_created: int = 0
    relationships_created: int = 0
