from collections.abc import Generator
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, declarative_base, sessionmaker

from app.core.config import settings


def ensure_sqlite_parent_dir(database_url: str) -> None:
    if not database_url.startswith("sqlite:///"):
        return
    db_path = Path(database_url.removeprefix("sqlite:///"))
    if db_path.is_absolute():
        db_path.parent.mkdir(parents=True, exist_ok=True)
        return
    db_path.parent.mkdir(parents=True, exist_ok=True)


ensure_sqlite_parent_dir(settings.DATABASE_URL)

engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False},
    echo=settings.DEBUG,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()
_is_schema_initialized = False


def ensure_schema_initialized() -> None:
    global _is_schema_initialized
    if _is_schema_initialized:
        return
    Base.metadata.create_all(bind=engine)
    _is_schema_initialized = True


def get_db() -> Generator[Session, None, None]:
    ensure_schema_initialized()
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
