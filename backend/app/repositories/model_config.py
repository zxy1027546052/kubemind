from sqlalchemy.orm import Session

from app.models.model_config import ModelConfig


def get_by_id(db: Session, config_id: int) -> ModelConfig | None:
    return db.query(ModelConfig).filter(ModelConfig.id == config_id).first()


def list_all(
    db: Session,
    offset: int = 0,
    limit: int = 20,
) -> tuple[int, list[ModelConfig]]:
    q = db.query(ModelConfig)
    total = q.count()
    items = q.order_by(ModelConfig.updated_at.desc()).offset(offset).limit(limit).all()
    return total, items


def create(db: Session, config: ModelConfig) -> ModelConfig:
    db.add(config)
    db.commit()
    db.refresh(config)
    return config


def update(db: Session, config: ModelConfig) -> ModelConfig:
    db.commit()
    db.refresh(config)
    return config


def delete(db: Session, config: ModelConfig) -> None:
    db.delete(config)
    db.commit()
