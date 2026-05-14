"""Tests for knowledge graph builder service."""

import json
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.models.cases import Case
from app.models.knowledge_graph import KnowledgeEntity, KnowledgeRelationship
from app.models.runbooks import Runbook
from app.core.database import Base
from app.services.knowledge_graph import (
    _link,
    _upsert_entity,
    build_from_cases,
    build_from_runbooks,
    get_graph_snapshot,
    rebuild_graph,
)


@pytest.fixture
def db():
    """In-memory SQLite session for isolated tests."""
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestingSessionLocal()
    yield session
    session.close()
    Base.metadata.drop_all(bind=engine)


class TestUpsertEntity:
    def test_creates_new(self, db):
        e = _upsert_entity(db, "test-pod", "k8s_pod", "pod:default/test-pod", {"status": "Running"})
        assert e.id is not None
        assert e.label == "test-pod"
        assert e.entity_type == "k8s_pod"
        assert e.external_id == "pod:default/test-pod"
        props = json.loads(e.properties)
        assert props["status"] == "Running"

    def test_updates_existing(self, db):
        e1 = _upsert_entity(db, "old-label", "k8s_pod", "pod:default/test-pod", {"status": "Pending"})
        db.commit()

        e2 = _upsert_entity(db, "new-label", "k8s_pod", "pod:default/test-pod", {"status": "Running"})
        db.commit()

        assert e2.id == e1.id
        assert e2.label == "new-label"
        props = json.loads(e2.properties)
        assert props["status"] == "Running"

        entities = db.query(KnowledgeEntity).all()
        assert len(entities) == 1


class TestLink:
    def test_creates_relationship(self, db):
        src = KnowledgeEntity(label="a", entity_type="k8s_pod", external_id="pod:a")
        tgt = KnowledgeEntity(label="b", entity_type="k8s_node", external_id="node:b")
        db.add(src)
        db.add(tgt)
        db.flush()

        rel = _link(db, src, tgt, "BELONGS_TO", 0.5)
        db.commit()
        assert rel is not None
        assert rel.relation_type == "BELONGS_TO"
        assert rel.weight == 0.5

    def test_skips_duplicate(self, db):
        src = KnowledgeEntity(label="a", entity_type="k8s_pod", external_id="pod:a")
        tgt = KnowledgeEntity(label="b", entity_type="k8s_node", external_id="node:b")
        db.add(src)
        db.add(tgt)
        db.flush()

        rel1 = KnowledgeRelationship(source_id=src.id, target_id=tgt.id, relation_type="BELONGS_TO")
        db.add(rel1)
        db.commit()

        rel2 = _link(db, src, tgt, "BELONGS_TO")
        assert rel2 is None


class TestBuildFromRunbooks:
    def test_extracts_entities(self, db):
        runbook = Runbook(
            title="MySQL连接池耗尽恢复",
            category="database",
            scenario="MySQL连接池耗尽导致大量API超时",
            tags="mysql,connection_pool",
        )
        db.add(runbook)
        db.commit()

        e, r = build_from_runbooks(db)

        assert e > 0
        runbook_entities = db.query(KnowledgeEntity).filter(
            KnowledgeEntity.entity_type == "runbook"
        ).all()
        assert len(runbook_entities) == 1
        assert runbook_entities[0].label == "MySQL连接池耗尽恢复"


class TestBuildFromCases:
    def test_extracts_entities(self, db):
        case = Case(
            title="MySQL Connection Pool Exhausted",
            category="connection_pool",
            symptom="API超时",
            root_cause="MySQL连接池耗尽，pod无法获取连接",
        )
        db.add(case)
        db.commit()

        e, r = build_from_cases(db)

        assert e > 0
        case_entities = db.query(KnowledgeEntity).filter(
            KnowledgeEntity.entity_type == "case"
        ).all()
        assert len(case_entities) == 1


class TestGraphSnapshot:
    def test_empty(self, db):
        result = get_graph_snapshot(db)
        assert result == {"nodes": [], "edges": []}

    def test_with_data(self, db):
        e1 = KnowledgeEntity(label="pod-1", entity_type="k8s_pod", external_id="pod:default/pod-1")
        e2 = KnowledgeEntity(label="node-1", entity_type="k8s_node", external_id="node:node-1")
        db.add(e1)
        db.add(e2)
        db.flush()
        rel = KnowledgeRelationship(source_id=e1.id, target_id=e2.id, relation_type="BELONGS_TO")
        db.add(rel)
        db.commit()

        result = get_graph_snapshot(db)
        assert len(result["nodes"]) == 2
        assert len(result["edges"]) == 1
        assert result["edges"][0]["relation_type"] == "BELONGS_TO"


class TestRebuildGraph:
    def test_from_all_sources(self, db):
        # Should handle gracefully even without K8s/Runbook/Case data
        result = rebuild_graph(db, source="all")
        assert "message" in result
        assert result["entities_created"] >= 0
        assert result["relationships_created"] >= 0
