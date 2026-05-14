"""Tests for knowledge graph API endpoints.

Creates an isolated FastAPI app with its own in-memory DB to avoid
interfering with the shared app's lifespan and other tests.
"""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.dependencies import get_db
from app.api.v1.endpoints.knowledge_graph import router
from app.core.database import Base


def _build_app():
    """Build a standalone FastAPI app with in-memory SQLite."""
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    def _get_db_override():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app = FastAPI()
    app.dependency_overrides[get_db] = _get_db_override
    app.include_router(router, prefix="/api/knowledge-graph")
    return app


@pytest.fixture
def client():
    app = _build_app()
    with TestClient(app) as c:
        yield c


def test_get_graph_returns_empty_snapshot(client) -> None:
    response = client.get("/api/knowledge-graph/graph")
    assert response.status_code == 200
    body = response.json()
    assert "nodes" in body
    assert "edges" in body


def test_get_graph_filters_by_entity_type(client) -> None:
    response = client.get("/api/knowledge-graph/graph?entity_type=k8s_pod")
    assert response.status_code == 200
    body = response.json()
    for node in body["nodes"]:
        assert node["entity_type"] == "k8s_pod"


def test_post_build_graph_rejects_invalid_source(client) -> None:
    response = client.post(
        "/api/knowledge-graph/graph/build",
        json={"source": "invalid"},
    )
    assert response.status_code == 422


def test_post_build_graph_accepts_runbooks_source(client) -> None:
    response = client.post(
        "/api/knowledge-graph/graph/build",
        json={"source": "runbooks"},
    )
    assert response.status_code == 200
    body = response.json()
    assert "entities_created" in body


def test_post_build_graph_accepts_all_source(client) -> None:
    response = client.post(
        "/api/knowledge-graph/graph/build",
        json={"source": "all"},
    )
    assert response.status_code == 200
    body = response.json()
    assert "entities_created" in body
    assert "relationships_created" in body
