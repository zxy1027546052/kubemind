"""Seed knowledge graph with sample entities and relationships for demo."""

import json
from datetime import datetime

from sqlalchemy.orm import Session

from app.models.knowledge_graph import KnowledgeEntity, KnowledgeRelationship

_SEED_ENTITIES = [
    {"label": "prod-cluster", "entity_type": "k8s_cluster", "external_id": "cluster:default", "properties": {"version": "v1.30.0"}},
    {"label": "k8s-master-1", "entity_type": "k8s_node", "external_id": "node:k8s-master-1", "properties": {"status": "Ready", "cpu": "8", "memory": "32Gi"}},
    {"label": "k8s-worker-1", "entity_type": "k8s_node", "external_id": "node:k8s-worker-1", "properties": {"status": "Ready", "cpu": "16", "memory": "64Gi"}},
    {"label": "k8s-worker-2", "entity_type": "k8s_node", "external_id": "node:k8s-worker-2", "properties": {"status": "Ready", "cpu": "16", "memory": "64Gi"}},
    {"label": "k8s-worker-3", "entity_type": "k8s_node", "external_id": "node:k8s-worker-3", "properties": {"status": "NotReady", "cpu": "16", "memory": "64Gi"}},
    {"label": "default", "entity_type": "k8s_namespace", "external_id": "ns:default", "properties": {}},
    {"label": "prod", "entity_type": "k8s_namespace", "external_id": "ns:prod", "properties": {}},
    {"label": "monitoring", "entity_type": "k8s_namespace", "external_id": "ns:monitoring", "properties": {}},
]


def _entity_key(entity_type: str, external_id: str | None) -> str:
    return f"{entity_type}:{external_id}"


def seed_knowledge_graph(db: Session) -> None:
    if db.query(KnowledgeEntity).first():
        return

    now = datetime.now()
    entities: dict[str, KnowledgeEntity] = {}

    for data in _SEED_ENTITIES:
        e = KnowledgeEntity(
            label=data["label"],
            entity_type=data["entity_type"],
            external_id=data.get("external_id"),
            properties=json.dumps(data.get("properties", {}), ensure_ascii=False),
            created_at=now,
            updated_at=now,
        )
        db.add(e)
        db.flush()
        entities[_entity_key(e.entity_type, e.external_id)] = e

    # Relationships: BELONGS_TO from nodes/namespaces to cluster
    rels = [
        ("k8s_node", "node:k8s-master-1", "k8s_cluster", "cluster:default", "BELONGS_TO"),
        ("k8s_node", "node:k8s-worker-1", "k8s_cluster", "cluster:default", "BELONGS_TO"),
        ("k8s_node", "node:k8s-worker-2", "k8s_cluster", "cluster:default", "BELONGS_TO"),
        ("k8s_node", "node:k8s-worker-3", "k8s_cluster", "cluster:default", "BELONGS_TO"),
        ("k8s_namespace", "ns:default", "k8s_cluster", "cluster:default", "BELONGS_TO"),
        ("k8s_namespace", "ns:prod", "k8s_cluster", "cluster:default", "BELONGS_TO"),
        ("k8s_namespace", "ns:monitoring", "k8s_cluster", "cluster:default", "BELONGS_TO"),
    ]

    for src_type, src_eid, tgt_type, tgt_eid, rel_type in rels:
        src = entities.get(_entity_key(src_type, src_eid))
        tgt = entities.get(_entity_key(tgt_type, tgt_eid))
        if src and tgt:
            db.add(KnowledgeRelationship(
                source_id=src.id,
                target_id=tgt.id,
                relation_type=rel_type,
                weight=1.0,
                created_at=now,
            ))

    db.commit()
