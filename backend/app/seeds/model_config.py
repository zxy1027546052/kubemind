from datetime import datetime

from sqlalchemy.orm import Session

from app.models.model_config import ModelConfig

SEED_DATA = [
    {"name": "OpenAI GPT-4o (默认)", "provider": "openai", "model_type": "llm",
     "endpoint": "https://api.openai.com/v1", "api_key": "", "model_name": "gpt-4o",
     "is_active": False, "config_json": '{"temperature": 0.7, "max_tokens": 4096}'},
    {"name": "OpenAI Embedding (默认)", "provider": "openai", "model_type": "embedding",
     "endpoint": "https://api.openai.com/v1", "api_key": "", "model_name": "text-embedding-3-small",
     "is_active": False, "config_json": '{"dimensions": 1536}'},
]


def seed_model_configs(db: Session) -> None:
    if db.query(ModelConfig).first():
        return
    now = datetime.now()
    for data in SEED_DATA:
        db.add(ModelConfig(**data, created_at=now, updated_at=now))
    db.commit()
