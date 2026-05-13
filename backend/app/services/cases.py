from datetime import datetime

from sqlalchemy.orm import Session

from app.models.cases import Case
from app.repositories import cases as repo
from app.schemas.cases import CaseCreate, CaseUpdate
from app.services import vector_db


def _sync_vector(db: Session, case: Case) -> None:
    vector_db.sync_record(
        db,
        source_type="cases",
        source_id=case.id,
        title=case.title,
        text=vector_db.build_text("cases", case),
    )


def list_cases(
    db: Session,
    query: str = "",
    category: str = "",
    severity: str = "",
    status: str = "",
    offset: int = 0,
    limit: int = 20,
) -> tuple[int, list[Case]]:
    return repo.list_with_filters(
        db, query=query, category=category, severity=severity, status=status, offset=offset, limit=limit
    )


def get_case(db: Session, case_id: int) -> Case | None:
    return repo.get_by_id(db, case_id)


def create_case(db: Session, payload: CaseCreate) -> Case:
    now = datetime.now()
    case = Case(**payload.model_dump(), created_at=now, updated_at=now)
    case = repo.create(db, case)
    _sync_vector(db, case)
    return case


def update_case(db: Session, case_id: int, payload: CaseUpdate) -> Case | None:
    case = repo.get_by_id(db, case_id)
    if not case:
        return None
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(case, key, value)
    case.updated_at = datetime.now()
    case = repo.update(db, case)
    _sync_vector(db, case)
    return case


def replace_case(db: Session, case_id: int, payload: CaseCreate) -> Case | None:
    case = repo.get_by_id(db, case_id)
    if not case:
        return None
    for key, value in payload.model_dump().items():
        setattr(case, key, value)
    case.updated_at = datetime.now()
    case = repo.update(db, case)
    _sync_vector(db, case)
    return case


def delete_case(db: Session, case_id: int) -> bool:
    case = repo.get_by_id(db, case_id)
    if not case:
        return False
    repo.delete(db, case)
    vector_db.remove_record("cases", case_id)
    return True
