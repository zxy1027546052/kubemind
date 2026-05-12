from sqlalchemy.orm import Session

from app.models.diagnosis import DiagnosisSession


def get_by_id(db: Session, session_id: int) -> DiagnosisSession | None:
    return db.query(DiagnosisSession).filter(DiagnosisSession.id == session_id).first()


def list_recent(db: Session, offset: int = 0, limit: int = 10) -> tuple[int, list[DiagnosisSession]]:
    q = db.query(DiagnosisSession)
    total = q.count()
    items = q.order_by(DiagnosisSession.created_at.desc()).offset(offset).limit(limit).all()
    return total, items


def create(db: Session, session: DiagnosisSession) -> DiagnosisSession:
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


def update(db: Session, session: DiagnosisSession) -> DiagnosisSession:
    db.commit()
    db.refresh(session)
    return session


def delete(db: Session, session: DiagnosisSession) -> None:
    db.delete(session)
    db.commit()
