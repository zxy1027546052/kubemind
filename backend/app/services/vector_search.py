"""统一相似检索入口 — 优先走 Milvus 向量召回，失败时回落到内存 TF-IDF."""

from __future__ import annotations

import logging
import math

from sqlalchemy.orm import Session

from app.models.cases import Case
from app.models.knowledge import Document
from app.models.runbooks import Runbook
from app.services import vector_db
from app.services.embedding import TFIDFEmbeddingProvider, get_embedding_provider

logger = logging.getLogger(__name__)

SearchResult = dict  # {id, source_type, title, score}

_TITLE_LOOKUP_MODELS = {
    "documents": Document,
    "cases": Case,
    "runbooks": Runbook,
}


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    if not a or not b:
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def _milvus_search(
    db: Session, query: str, source_types: list[str], top_k: int
) -> list[SearchResult] | None:
    """走 Milvus 召回；不可用或异常返回 None 让上层 fallback."""
    if not vector_db.is_available():
        return None
    try:
        provider = get_embedding_provider(db)
        qvec = provider.embed([query])
        if not qvec or not qvec[0]:
            return None
        hits = vector_db.search(qvec[0], source_types, top_k)
    except Exception as e:
        logger.warning("Milvus search failed, falling back to TF-IDF: %s", e)
        return None

    if not hits:
        return []

    results: list[SearchResult] = []
    for h in hits:
        st = h.get("source_type")
        sid = h.get("source_id")
        title = h.get("title") or ""
        if not title and st in _TITLE_LOOKUP_MODELS:
            row = db.get(_TITLE_LOOKUP_MODELS[st], sid)
            title = getattr(row, "title", "") if row else ""
        results.append({
            "id": int(sid) if sid is not None else 0,
            "source_type": st,
            "title": title,
            "score": round(float(h.get("score", 0.0)), 4),
        })
    return results


def _tfidf_fallback(
    db: Session, query: str, source_types: list[str], top_k: int
) -> list[SearchResult]:
    items: list[dict] = []
    corpus: list[str] = []

    if "documents" in source_types:
        for doc in db.query(Document).all():
            text = vector_db.build_text("documents", doc)
            items.append({"id": doc.id, "source_type": "documents", "title": doc.title})
            corpus.append(text)

    if "cases" in source_types:
        for case in db.query(Case).all():
            text = vector_db.build_text("cases", case)
            items.append({"id": case.id, "source_type": "cases", "title": case.title})
            corpus.append(text)

    if "runbooks" in source_types:
        for rb in db.query(Runbook).all():
            text = vector_db.build_text("runbooks", rb)
            items.append({"id": rb.id, "source_type": "runbooks", "title": rb.title})
            corpus.append(text)

    if not items:
        return []

    provider = TFIDFEmbeddingProvider(corpus + [query])
    query_vec = provider.embed([query])[0]
    corpus_vecs = provider.embed(corpus)

    results: list[SearchResult] = []
    for i, item in enumerate(items):
        score = _cosine_similarity(query_vec, corpus_vecs[i])
        if score > 0.01:
            results.append({
                "id": item["id"],
                "source_type": item["source_type"],
                "title": item["title"],
                "score": round(score, 4),
            })
    results.sort(key=lambda r: r["score"], reverse=True)
    return results[:top_k]


def search_similar(
    db: Session,
    query: str,
    source_types: list[str] | None = None,
    top_k: int = 5,
) -> list[SearchResult]:
    if not query.strip():
        return []
    types = source_types or ["documents", "cases", "runbooks"]

    milvus_results = _milvus_search(db, query, types, top_k)
    if milvus_results is not None:
        return milvus_results

    return _tfidf_fallback(db, query, types, top_k)
