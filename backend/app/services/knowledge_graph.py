"""Knowledge graph builder — populates entities and relationships from
K8s resources, runbooks, and historical cases."""

from __future__ import annotations

import json
import logging
from typing import Any

from sqlalchemy.orm import Session

from app.models.cases import Case
from app.models.knowledge_graph import KnowledgeEntity, KnowledgeRelationship
from app.models.runbooks import Runbook
from app.services.k8s import get_k8s_client

logger = logging.getLogger(__name__)


# ---- helpers ----

def _upsert_entity(
    db: Session, label: str, entity_type: str, external_id: str | None = None, props: dict | None = None
) -> KnowledgeEntity:
    entity = (
        db.query(KnowledgeEntity)
        .filter(
            KnowledgeEntity.entity_type == entity_type,
            KnowledgeEntity.external_id == external_id,
        )
        .first()
    )
    if entity:
        entity.label = label
        entity.properties = json.dumps(props or {}, ensure_ascii=False)
    else:
        entity = KnowledgeEntity(
            label=label,
            entity_type=entity_type,
            external_id=external_id,
            properties=json.dumps(props or {}, ensure_ascii=False),
        )
        db.add(entity)
        db.flush()
    return entity


def _link(
    db: Session, source: KnowledgeEntity, target: KnowledgeEntity, relation_type: str, weight: float = 1.0
) -> KnowledgeRelationship | None:
    existing = (
        db.query(KnowledgeRelationship)
        .filter(
            KnowledgeRelationship.source_id == source.id,
            KnowledgeRelationship.target_id == target.id,
            KnowledgeRelationship.relation_type == relation_type,
        )
        .first()
    )
    if existing:
        return None
    rel = KnowledgeRelationship(
        source_id=source.id,
        target_id=target.id,
        relation_type=relation_type,
        weight=weight,
    )
    db.add(rel)
    return rel


# ---- K8s builder ----

def build_from_k8s(db: Session) -> tuple[int, int]:
    """Scan K8s resources and populate entities + relationships."""
    client = get_k8s_client()
    if not client.connected:
        logger.warning("K8s client not connected, skipping graph build")
        return 0, 0

    entities_added = 0
    rels_added = 0

    # cluster
    cluster = _upsert_entity(db, "default", "k8s_cluster", "cluster:default", {"version": client.version})
    entities_added += 1

    # nodes
    node_entities: dict[str, KnowledgeEntity] = {}
    for node in client.get_nodes():
        e = _upsert_entity(
            db, node["name"], "k8s_node", f"node:{node['name']}",
            {"status": node["status"], "cpu": node.get("cpu", ""), "memory": node.get("memory", "")},
        )
        node_entities[node["name"]] = e
        entities_added += 1
        rel = _link(db, e, cluster, "BELONGS_TO")
        if rel:
            rels_added += 1

    # pods (all namespaces)
    pod_entities: dict[str, KnowledgeEntity] = {}
    namespace_entities: dict[str, KnowledgeEntity] = {}
    for pod in client.get_pods():
        ns_name = pod["namespace"]
        if ns_name and ns_name not in namespace_entities:
            ns_entity = _upsert_entity(db, ns_name, "k8s_namespace", f"ns:{ns_name}")
            namespace_entities[ns_name] = ns_entity
            entities_added += 1
            rel = _link(db, ns_entity, cluster, "BELONGS_TO")
            if rel:
                rels_added += 1

        ns_entity = namespace_entities.get(ns_name)
        e = _upsert_entity(
            db, pod["name"], "k8s_pod", f"pod:{ns_name}/{pod['name']}",
            {"namespace": ns_name, "status": pod["status"], "node": pod.get("node", "")},
        )
        pod_entities[f"{ns_name}/{pod['name']}"] = e
        entities_added += 1

        # pod → namespace
        if ns_entity:
            rel = _link(db, e, ns_entity, "BELONGS_TO")
            if rel:
                rels_added += 1

        # pod → node
        node_name = pod.get("node", "")
        if node_name and node_name in node_entities:
            rel = _link(db, e, node_entities[node_name], "BELONGS_TO")
            if rel:
                rels_added += 1

    logger.info(
        "K8s graph built: %d entities, %d relationships",
        entities_added, rels_added,
    )
    return entities_added, rels_added


# ---- Runbook / Case builder ----

_CATEGORY_KEYWORDS: dict[str, list[str]] = {
    "k8s_pod": ["pod", "crashloopbackoff", "oom", "container", "deployment"],
    "k8s_node": ["node", "notready", "disk", "memory", "cpu"],
    "k8s_namespace": ["namespace"],
    "alert": ["alert", "prometheus", "alertmanager"],
    "anomaly": ["anomaly", "spike", "drop", "outlier"],
}

_RESOLVE_CACHE: dict[tuple[str, str | None], KnowledgeEntity | None] = {}


def _resolve_or_create_entity(
    db: Session, label: str, entity_type: str, external_id: str | None = None
) -> KnowledgeEntity:
    cache_key = (entity_type, external_id)
    if cache_key in _RESOLVE_CACHE:
        return _RESOLVE_CACHE[cache_key]  # type: ignore[return-value]
    entity = _upsert_entity(db, label, entity_type, external_id)
    _RESOLVE_CACHE[cache_key] = entity
    return entity


def _infer_entity_type_from_text(text: str) -> str:
    lower = text.lower()
    for entity_type, keywords in _CATEGORY_KEYWORDS.items():
        if any(kw in lower for kw in keywords):
            return entity_type
    return "k8s_pod"


def _extract_labels_from_text(text: str, max_labels: int = 3) -> list[str]:
    """Heuristic: split by common delimiters and return short tokens."""
    import re

    tokens = re.split(r"[，,;；\s\n]+", text)
    return [t for t in tokens if 2 <= len(t) <= 60][:max_labels]


def build_from_runbooks(db: Session) -> tuple[int, int]:
    """Extract entities and relationships from runbook records."""
    entities_added = 0
    rels_added = 0

    runbooks = db.query(Runbook).all()
    for rb in runbooks:
        runbook_entity = _resolve_or_create_entity(
            db, rb.title, "runbook", f"runbook:{rb.id}",
        )
        entities_added += 1

        # Infer related entities from category and scenario text
        combined = f"{rb.category} {rb.scenario} {rb.tags}"
        ref_labels = _extract_labels_from_text(rb.scenario or "")

        entity_type = _infer_entity_type_from_text(combined)
        for label in ref_labels:
            ref_entity = _resolve_or_create_entity(
                db, label, entity_type, f"inferred:{label}",
            )
            entities_added += 1
            rel = _link(db, runbook_entity, ref_entity, "MITIGATES")
            if rel:
                rels_added += 1

    logger.info(
        "Runbook graph built: %d entities, %d relationships",
        entities_added, rels_added,
    )
    return entities_added, rels_added


def build_from_cases(db: Session) -> tuple[int, int]:
    """Extract entities and relationships from historical case records."""
    entities_added = 0
    rels_added = 0

    cases = db.query(Case).all()
    for case in cases:
        case_entity = _resolve_or_create_entity(
            db, case.title, "case", f"case:{case.id}",
        )
        entities_added += 1

        combined = f"{case.category} {case.symptom} {case.root_cause}"
        ref_labels = _extract_labels_from_text(case.root_cause or "")

        entity_type = _infer_entity_type_from_text(combined)
        for label in ref_labels:
            ref_entity = _resolve_or_create_entity(
                db, label, entity_type, f"inferred:{label}",
            )
            entities_added += 1
            rel = _link(db, case_entity, ref_entity, "CAUSES")
            if rel:
                rels_added += 1

    logger.info(
        "Case graph built: %d entities, %d relationships",
        entities_added, rels_added,
    )
    return entities_added, rels_added


# ---- unified builder ----

def rebuild_graph(db: Session, source: str = "all") -> dict[str, Any]:
    """Rebuild knowledge graph from the specified source(s)."""
    total_entities = 0
    total_rels = 0

    if source in ("k8s", "all"):
        e, r = build_from_k8s(db)
        total_entities += e
        total_rels += r

    if source in ("runbooks", "all"):
        e, r = build_from_runbooks(db)
        total_entities += e
        total_rels += r

    if source in ("cases", "all"):
        e, r = build_from_cases(db)
        total_entities += e
        total_rels += r

    db.commit()
    return {
        "message": f"Graph rebuilt from source={source}",
        "entities_created": total_entities,
        "relationships_created": total_rels,
    }


# ---- graph query ----

def get_graph_snapshot(db: Session, entity_type: str | None = None, limit: int = 500) -> dict[str, Any]:
    """Return nodes and edges for frontend visualization."""
    query = db.query(KnowledgeEntity)
    if entity_type:
        query = query.filter(KnowledgeEntity.entity_type == entity_type)

    entities = query.order_by(KnowledgeEntity.updated_at.desc()).limit(limit).all()
    entity_ids = {e.id for e in entities}

    relationships = (
        db.query(KnowledgeRelationship)
        .filter(
            KnowledgeRelationship.source_id.in_(entity_ids),
            KnowledgeRelationship.target_id.in_(entity_ids),
        )
        .all()
    )

    return {
        "nodes": [
            {
                "id": e.id,
                "label": e.label,
                "entity_type": e.entity_type,
                "external_id": e.external_id,
                "properties": e.properties,
            }
            for e in entities
        ],
        "edges": [
            {
                "id": r.id,
                "source": r.source_id,
                "target": r.target_id,
                "relation_type": r.relation_type,
                "weight": r.weight,
            }
            for r in relationships
        ],
    }
