from datetime import datetime

from sqlalchemy.orm import Session

from app.models.runbooks import Runbook
from app.repositories import runbooks as repo
from app.schemas.runbooks import RunbookCreate, RunbookUpdate
from app.services import vector_db


def _sync_vector(db: Session, runbook: Runbook) -> None:
    vector_db.sync_record(
        db,
        source_type="runbooks",
        source_id=runbook.id,
        title=runbook.title,
        text=vector_db.build_text("runbooks", runbook),
    )


def list_runbooks(
    db: Session, query: str = "", category: str = "", offset: int = 0, limit: int = 20
) -> tuple[int, list[Runbook]]:
    return repo.list_with_filters(db, query=query, category=category, offset=offset, limit=limit)


def get_runbook(db: Session, runbook_id: int) -> Runbook | None:
    return repo.get_by_id(db, runbook_id)


def create_runbook(db: Session, payload: RunbookCreate) -> Runbook:
    now = datetime.now()
    runbook = Runbook(**payload.model_dump(), created_at=now, updated_at=now)
    runbook = repo.create(db, runbook)
    _sync_vector(db, runbook)
    return runbook


def update_runbook(db: Session, runbook_id: int, payload: RunbookUpdate) -> Runbook | None:
    runbook = repo.get_by_id(db, runbook_id)
    if not runbook:
        return None
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(runbook, key, value)
    runbook.updated_at = datetime.now()
    runbook = repo.update(db, runbook)
    _sync_vector(db, runbook)
    return runbook


def replace_runbook(db: Session, runbook_id: int, payload: RunbookCreate) -> Runbook | None:
    runbook = repo.get_by_id(db, runbook_id)
    if not runbook:
        return None
    for key, value in payload.model_dump().items():
        setattr(runbook, key, value)
    runbook.updated_at = datetime.now()
    runbook = repo.update(db, runbook)
    _sync_vector(db, runbook)
    return runbook


def delete_runbook(db: Session, runbook_id: int) -> bool:
    runbook = repo.get_by_id(db, runbook_id)
    if not runbook:
        return False
    repo.delete(db, runbook)
    vector_db.remove_record("runbooks", runbook_id)
    return True
