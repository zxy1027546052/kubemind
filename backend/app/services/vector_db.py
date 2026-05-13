"""Milvus 向量数据库封装 — 统一 KubeMind 知识库的向量化读写入口.

设计原则:
- 惰性连接、惰性建集合，Milvus 不可用时所有公开函数返回 False / 空结果而不抛
- 单一集合 `settings.VECTOR_DB_COLLECTION_NAME`，使用复合主键 `pk = "{source_type}:{source_id}"`
- 维度根据首次写入的 embedding 自动决定；后续写入维度必须一致
- 上层 (services/knowledge|cases|runbooks) 调用 `sync_record / remove_record`，向量层错误不影响业务事务
"""

from __future__ import annotations

import logging
import threading
from typing import Any

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.cases import Case
from app.models.knowledge import Document
from app.models.runbooks import Runbook
from app.services.embedding import get_embedding_provider

logger = logging.getLogger(__name__)

SOURCE_TYPES = ("documents", "cases", "runbooks")

_client: Any | None = None
_client_lock = threading.Lock()
_collection_ready_dim: int | None = None
_unavailable_logged = False


class VectorDBUnavailable(RuntimeError):
    """Milvus 未配置或连接失败时抛出，调用方应捕获并降级."""


def _build_text(source_type: str, obj: Document | Case | Runbook) -> str:
    if source_type == "documents":
        doc: Document = obj  # type: ignore[assignment]
        return f"{doc.title} {doc.content}"
    if source_type == "cases":
        case: Case = obj  # type: ignore[assignment]
        return f"{case.title} {case.symptom} {case.root_cause} {case.steps} {case.impact} {case.conclusion}"
    if source_type == "runbooks":
        rb: Runbook = obj  # type: ignore[assignment]
        return f"{rb.title} {rb.scenario} {rb.steps} {rb.risk} {rb.rollback}"
    raise ValueError(f"unknown source_type: {source_type}")


def build_text(source_type: str, obj: Document | Case | Runbook) -> str:
    """Public helper for callers that need to embed-on-write."""
    return _build_text(source_type, obj)


def _make_pk(source_type: str, source_id: int) -> str:
    return f"{source_type}:{source_id}"


def _get_client() -> Any:
    """惰性创建 MilvusClient；连接失败抛 VectorDBUnavailable."""
    global _client, _unavailable_logged

    if _client is not None:
        return _client

    if not settings.VECTOR_DB_HOST:
        raise VectorDBUnavailable("VECTOR_DB_HOST is empty")

    with _client_lock:
        if _client is not None:
            return _client
        try:
            from pymilvus import MilvusClient
        except ImportError as e:
            raise VectorDBUnavailable(f"pymilvus not installed: {e}") from e

        uri = f"http://{settings.VECTOR_DB_HOST}:{settings.VECTOR_DB_PORT}"
        token = f"{settings.VECTOR_DB_USER}:{settings.VECTOR_DB_PASSWORD}" if settings.VECTOR_DB_USER else ""
        try:
            client = MilvusClient(uri=uri, token=token)
            # 触发一次实际请求以暴露连接问题
            client.list_collections()
        except Exception as e:
            raise VectorDBUnavailable(f"cannot connect to Milvus at {uri}: {e}") from e

        _client = client
        _unavailable_logged = False
        logger.info("Milvus client connected: %s", uri)
        return _client


def is_available() -> bool:
    """探测 Milvus 是否可用 (惰性)，失败仅记录一次警告."""
    global _unavailable_logged
    try:
        _get_client()
        return True
    except VectorDBUnavailable as e:
        if not _unavailable_logged:
            logger.warning("Milvus unavailable, falling back to TF-IDF: %s", e)
            _unavailable_logged = True
        return False


def _build_schema(dim: int) -> tuple[Any, Any]:
    from pymilvus import DataType, MilvusClient

    client = _get_client()
    schema = MilvusClient.create_schema(auto_id=False, enable_dynamic_field=False)
    schema.add_field("pk", DataType.VARCHAR, is_primary=True, max_length=64)
    schema.add_field("source_type", DataType.VARCHAR, max_length=16)
    schema.add_field("source_id", DataType.INT64)
    schema.add_field("title", DataType.VARCHAR, max_length=512)
    schema.add_field("vector", DataType.FLOAT_VECTOR, dim=dim)

    index_params = client.prepare_index_params()
    index_params.add_index(field_name="vector", index_type="AUTOINDEX", metric_type="COSINE")
    return schema, index_params


def ensure_collection(dim: int) -> None:
    """不存在则创建集合；已存在则校验维度一致 (维度冲突会日志告警，不重建)."""
    global _collection_ready_dim
    if _collection_ready_dim == dim:
        return

    client = _get_client()
    name = settings.VECTOR_DB_COLLECTION_NAME
    if client.has_collection(name):
        try:
            desc = client.describe_collection(name)
            existing_dim = None
            for f in desc.get("fields", []):
                if f.get("name") == "vector":
                    params = f.get("params") or {}
                    existing_dim = int(params.get("dim", 0)) or None
                    break
            if existing_dim and existing_dim != dim:
                logger.warning(
                    "Milvus collection %s dim mismatch (existing=%s, new=%s); "
                    "ignoring new dim, run reindex script with --drop to rebuild",
                    name, existing_dim, dim,
                )
            _collection_ready_dim = existing_dim or dim
            return
        except Exception as e:
            logger.warning("describe_collection failed, will reuse: %s", e)
            _collection_ready_dim = dim
            return

    schema, index_params = _build_schema(dim)
    client.create_collection(collection_name=name, schema=schema, index_params=index_params)
    _collection_ready_dim = dim
    logger.info("Milvus collection created: %s (dim=%d)", name, dim)


def drop_collection() -> bool:
    """删除集合，供 reindex --drop 使用."""
    global _collection_ready_dim
    try:
        client = _get_client()
    except VectorDBUnavailable:
        return False
    name = settings.VECTOR_DB_COLLECTION_NAME
    if client.has_collection(name):
        client.drop_collection(name)
        logger.info("Milvus collection dropped: %s", name)
    _collection_ready_dim = None
    return True


def upsert(items: list[dict]) -> int:
    """批量写入。items 必须包含 pk/source_type/source_id/title/vector."""
    if not items:
        return 0
    client = _get_client()
    client.upsert(collection_name=settings.VECTOR_DB_COLLECTION_NAME, data=items)
    return len(items)


def delete(source_type: str, source_id: int) -> None:
    try:
        client = _get_client()
    except VectorDBUnavailable:
        return
    name = settings.VECTOR_DB_COLLECTION_NAME
    if not client.has_collection(name):
        return
    pk = _make_pk(source_type, source_id)
    try:
        client.delete(collection_name=name, filter=f'pk == "{pk}"')
    except Exception as e:
        logger.warning("Milvus delete failed for %s: %s", pk, e)


def search(query_vec: list[float], source_types: list[str], top_k: int) -> list[dict]:
    client = _get_client()
    name = settings.VECTOR_DB_COLLECTION_NAME
    if not client.has_collection(name):
        return []

    types_quoted = ", ".join(f'"{t}"' for t in source_types)
    filter_expr = f"source_type in [{types_quoted}]"

    res = client.search(
        collection_name=name,
        data=[query_vec],
        limit=top_k,
        filter=filter_expr,
        output_fields=["source_type", "source_id", "title"],
        search_params={"metric_type": "COSINE"},
    )
    hits: list[dict] = []
    if not res:
        return hits
    for hit in res[0]:
        entity = hit.get("entity") or {}
        hits.append({
            "source_type": entity.get("source_type"),
            "source_id": entity.get("source_id"),
            "title": entity.get("title"),
            "score": float(hit.get("distance", 0.0)),
        })
    return hits


def sync_record(db: Session, source_type: str, source_id: int, title: str, text: str) -> None:
    """业务侧 create/update 调用：embed + upsert。所有异常吞掉只记日志."""
    if not text.strip():
        return
    try:
        provider = get_embedding_provider(db)
        vec = provider.embed([text])[0]
        if not vec:
            return
        ensure_collection(len(vec))
        upsert([{
            "pk": _make_pk(source_type, source_id),
            "source_type": source_type,
            "source_id": int(source_id),
            "title": title[:512],
            "vector": vec,
        }])
    except VectorDBUnavailable:
        pass  # 已在 is_available() / _get_client() 中记录
    except Exception as e:
        logger.warning("vector sync failed (%s:%s): %s", source_type, source_id, e)


def remove_record(source_type: str, source_id: int) -> None:
    """业务侧 delete 调用，吞异常."""
    try:
        delete(source_type, source_id)
    except VectorDBUnavailable:
        pass
    except Exception as e:
        logger.warning("vector remove failed (%s:%s): %s", source_type, source_id, e)


def try_init_on_startup(db: Session | None = None) -> None:
    """启动钩子：探测 Milvus + 若有 active embedding config 则预建集合."""
    if not is_available():
        return
    if db is None:
        return
    try:
        provider = get_embedding_provider(db)
        # 用一条短文本探测维度
        probe = provider.embed(["kubemind"])
        if probe and probe[0]:
            ensure_collection(len(probe[0]))
    except Exception as e:
        logger.warning("Milvus startup init skipped: %s", e)
