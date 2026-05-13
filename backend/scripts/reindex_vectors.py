"""一次性回填脚本：把 SQLite 中的 documents / cases / runbooks 全量写入 Milvus.

Usage (从 backend/ 目录下执行):
    python -m scripts.reindex_vectors            # 增量 upsert
    python -m scripts.reindex_vectors --drop     # 先删除集合再重建

Milvus 必须已在 settings.VECTOR_DB_HOST:PORT 可达，且 model_config 表中应至少
有一条 model_type='embedding' 且 is_active=True 的记录；否则会用本地 TF-IDF
embedding 顶替，维度由 TF-IDF 词表决定 (不推荐用于生产)。
"""

from __future__ import annotations

import argparse
import sys
import time
from typing import Iterable

from sqlalchemy.orm import Session

from app.core.database import Base, SessionLocal, engine
from app.models.cases import Case
from app.models.knowledge import Document
from app.models.runbooks import Runbook
from app.services import vector_db
from app.services.embedding import get_embedding_provider

BATCH_SIZE = 32


def _iter_batches(items: list, size: int) -> Iterable[list]:
    for i in range(0, len(items), size):
        yield items[i : i + size]


def _reindex_table(db: Session, source_type: str, rows: list) -> int:
    if not rows:
        print(f"  [{source_type}] no rows")
        return 0

    provider = get_embedding_provider(db)
    written = 0
    for batch in _iter_batches(rows, BATCH_SIZE):
        texts = [vector_db.build_text(source_type, r) for r in batch]
        vecs = provider.embed(texts)
        if not vecs or not vecs[0]:
            print(f"  [{source_type}] embedding returned empty, abort")
            return written
        dim = len(vecs[0])
        vector_db.ensure_collection(dim)

        payload = [
            {
                "pk": f"{source_type}:{row.id}",
                "source_type": source_type,
                "source_id": int(row.id),
                "title": (row.title or "")[:512],
                "vector": vec,
            }
            for row, vec in zip(batch, vecs)
        ]
        vector_db.upsert(payload)
        written += len(payload)
        print(f"  [{source_type}] +{len(payload)} (total {written}/{len(rows)})")
    return written


def main() -> int:
    parser = argparse.ArgumentParser(description="Rebuild KubeMind vector index in Milvus")
    parser.add_argument("--drop", action="store_true", help="drop collection before reindex")
    args = parser.parse_args()

    if not vector_db.is_available():
        print("ERROR: Milvus is not available. Check VECTOR_DB_HOST/PORT in .env", file=sys.stderr)
        return 2

    if args.drop:
        if vector_db.drop_collection():
            print("collection dropped")

    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        start = time.time()
        total = 0
        print("reindexing documents…")
        total += _reindex_table(db, "documents", db.query(Document).all())
        print("reindexing cases…")
        total += _reindex_table(db, "cases", db.query(Case).all())
        print("reindexing runbooks…")
        total += _reindex_table(db, "runbooks", db.query(Runbook).all())
        elapsed = time.time() - start
        print(f"done: {total} vectors written in {elapsed:.2f}s")
    finally:
        db.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
