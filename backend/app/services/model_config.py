from datetime import datetime

from sqlalchemy.orm import Session

from app.models.model_config import ModelConfig
from app.repositories import model_config as repo
from app.schemas.model_config import ModelConfigCreate, ModelConfigUpdate


def list_model_configs(
    db: Session, offset: int = 0, limit: int = 20
) -> tuple[int, list[ModelConfig]]:
    return repo.list_all(db, offset=offset, limit=limit)


def get_model_config(db: Session, config_id: int) -> ModelConfig | None:
    return repo.get_by_id(db, config_id)


def create_model_config(db: Session, payload: ModelConfigCreate) -> ModelConfig:
    now = datetime.now()
    config = ModelConfig(**payload.model_dump(), created_at=now, updated_at=now)
    return repo.create(db, config)


def update_model_config(db: Session, config_id: int, payload: ModelConfigUpdate) -> ModelConfig | None:
    config = repo.get_by_id(db, config_id)
    if not config:
        return None
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(config, key, value)
    config.updated_at = datetime.now()
    return repo.update(db, config)


def delete_model_config(db: Session, config_id: int) -> bool:
    config = repo.get_by_id(db, config_id)
    if not config:
        return False
    repo.delete(db, config)
    return True


def test_model_connection(db: Session, config_id: int) -> tuple[bool, str]:
    config = repo.get_by_id(db, config_id)
    if not config:
        return False, "Model config not found"
    if not config.api_key:
        return False, "API key not configured"

    import json
    import urllib.request

    try:
        payload = json.dumps({
            "model": config.model_name,
            "messages": [{"role": "user", "content": "hi"}],
            "max_tokens": 1,
        }).encode("utf-8")
        req = urllib.request.Request(
            f"{config.endpoint.rstrip('/')}/chat/completions",
            data=payload,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {config.api_key}",
            },
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            if resp.status == 200:
                return True, f"Connection successful — {config.provider}/{config.model_name}"
            return False, f"HTTP {resp.status}"
    except urllib.error.HTTPError as e:
        return False, f"HTTP {e.code}: {e.reason}"
    except Exception as e:
        return False, str(e)
