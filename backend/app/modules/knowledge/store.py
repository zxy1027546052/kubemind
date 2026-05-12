import json
from datetime import datetime

from app.core.config import DOCUMENTS_FILE
from app.core.schemas import Document, DocumentCreate


def _seed_documents() -> list[dict]:
    now = datetime.now().isoformat()
    return [
        {
            "id": 1,
            "title": "Runbook: MySQL Slow Query / Connection Issue",
            "type": "Runbook",
            "category": "slow_sql",
            "size": "-",
            "content": "Check slow queries, connection counts, lock waits, and pool settings.",
            "created_at": now,
            "updated_at": now,
        },
        {
            "id": 2,
            "title": "Runbook: Disk IO Saturation",
            "type": "Runbook",
            "category": "io_saturation",
            "size": "-",
            "content": "Inspect iostat, identify hot processes, and evaluate disk throughput.",
            "created_at": now,
            "updated_at": now,
        },
        {
            "id": 3,
            "title": "Runbook: Packet Loss / Bandwidth Saturation",
            "type": "Runbook",
            "category": "network_issue",
            "size": "-",
            "content": "Check NIC traffic, retransmits, error packets, and node link status.",
            "created_at": now,
            "updated_at": now,
        },
    ]


def _ensure_file() -> None:
    if not DOCUMENTS_FILE.exists():
        DOCUMENTS_FILE.write_text(
            json.dumps(_seed_documents(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )


def load_documents() -> list[Document]:
    _ensure_file()
    raw = json.loads(DOCUMENTS_FILE.read_text(encoding="utf-8"))
    return [Document(**item) for item in raw]


def save_documents(documents: list[Document]) -> None:
    payload = [item.model_dump(mode="json") for item in documents]
    DOCUMENTS_FILE.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def list_documents(query: str = "", category: str = "") -> list[Document]:
    documents = load_documents()
    result = documents
    if query:
        q = query.lower()
        result = [
            item
            for item in result
            if q in item.title.lower()
            or q in item.content.lower()
            or q in item.category.lower()
        ]
    if category:
        result = [item for item in result if item.category == category]
    return result


def create_document(payload: DocumentCreate) -> Document:
    documents = load_documents()
    now = datetime.now()
    next_id = max((item.id for item in documents), default=0) + 1
    document = Document(
        id=next_id,
        created_at=now,
        updated_at=now,
        **payload.model_dump(),
    )
    documents.append(document)
    save_documents(documents)
    return document


def delete_document(document_id: int) -> bool:
    documents = load_documents()
    filtered = [item for item in documents if item.id != document_id]
    if len(filtered) == len(documents):
        return False
    save_documents(filtered)
    return True
