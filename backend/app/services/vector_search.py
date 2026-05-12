import math

from sqlalchemy.orm import Session

from app.models.cases import Case
from app.models.knowledge import Document
from app.models.runbooks import Runbook
from app.services.embedding import TFIDFEmbeddingProvider, get_embedding_provider

SearchResult = dict  # {id, source_type, title, score}


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    if not a or not b:
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def _get_text_for_document(doc: Document) -> str:
    return f"{doc.title} {doc.content}"


def _get_text_for_case(case: Case) -> str:
    return f"{case.title} {case.symptom} {case.root_cause} {case.steps} {case.impact} {case.conclusion}"


def _get_text_for_runbook(runbook: Runbook) -> str:
    return f"{runbook.title} {runbook.scenario} {runbook.steps} {runbook.risk} {runbook.rollback}"


def search_similar(
    db: Session,
    query: str,
    source_types: list[str] | None = None,
    top_k: int = 5,
) -> list[SearchResult]:
    if not query.strip():
        return []

    if source_types is None:
        source_types = ["documents", "cases", "runbooks"]

    # Collect all items and their texts
    items: list[dict] = []
    corpus: list[str] = []

    if "documents" in source_types:
        for doc in db.query(Document).all():
            text = _get_text_for_document(doc)
            items.append({"id": doc.id, "source_type": "documents", "title": doc.title, "text": text})
            corpus.append(text)

    if "cases" in source_types:
        for case in db.query(Case).all():
            text = _get_text_for_case(case)
            items.append({"id": case.id, "source_type": "cases", "title": case.title, "text": text})
            corpus.append(text)

    if "runbooks" in source_types:
        for runbook in db.query(Runbook).all():
            text = _get_text_for_runbook(runbook)
            items.append({"id": runbook.id, "source_type": "runbooks", "title": runbook.title, "text": text})
            corpus.append(text)

    if not items:
        return []

    # Fit TF-IDF on corpus + query, then embed
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
