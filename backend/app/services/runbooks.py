from datetime import datetime

from sqlalchemy.orm import Session

from app.models.runbooks import Runbook
from app.repositories import runbooks as repo
from app.schemas.runbooks import RunbookCreate, RunbookUpdate


def list_runbooks(
    db: Session, query: str = "", category: str = "", offset: int = 0, limit: int = 20
) -> tuple[int, list[Runbook]]:
    return repo.list_with_filters(db, query=query, category=category, offset=offset, limit=limit)


def get_runbook(db: Session, runbook_id: int) -> Runbook | None:
    return repo.get_by_id(db, runbook_id)


def create_runbook(db: Session, payload: RunbookCreate) -> Runbook:
    now = datetime.now()
    runbook = Runbook(**payload.model_dump(), created_at=now, updated_at=now)
    return repo.create(db, runbook)


def update_runbook(db: Session, runbook_id: int, payload: RunbookUpdate) -> Runbook | None:
    runbook = repo.get_by_id(db, runbook_id)
    if not runbook:
        return None
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(runbook, key, value)
    runbook.updated_at = datetime.now()
    return repo.update(db, runbook)


def replace_runbook(db: Session, runbook_id: int, payload: RunbookCreate) -> Runbook | None:
    runbook = repo.get_by_id(db, runbook_id)
    if not runbook:
        return None
    for key, value in payload.model_dump().items():
        setattr(runbook, key, value)
    runbook.updated_at = datetime.now()
    return repo.update(db, runbook)


def delete_runbook(db: Session, runbook_id: int) -> bool:
    runbook = repo.get_by_id(db, runbook_id)
    if not runbook:
        return False
    repo.delete(db, runbook)
    return True
