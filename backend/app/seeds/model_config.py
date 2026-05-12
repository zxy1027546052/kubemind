from datetime import datetime

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.model_config import ModelConfig

SEED_DATA: list[dict] = []


def seed_model_configs(db: Session) -> None:
    if db.query(ModelConfig).first():
        return
    now = datetime.now()

    # DeepSeek LLM config from environment
    if settings.DEEPSEEK_AUTH_TOKEN:
        db.add(ModelConfig(
            name="DeepSeek Chat (默认)",
            provider="deepseek",
            model_type="llm",
            endpoint=settings.DEEPSEEK_BASE_URL.rstrip("/") + "/v1",
            api_key=settings.DEEPSEEK_AUTH_TOKEN,
            model_name=settings.DEEPSEEK_MODEL_NAME,
            is_active=True,
            config_json='{"temperature": 0.7, "max_tokens": 4096}',
            created_at=now,
            updated_at=now,
        ))

    # OpenAI fallback (inactive, for reference)
    db.add(ModelConfig(
        name="OpenAI GPT-4o (备用)",
        provider="openai",
        model_type="llm",
        endpoint="https://api.openai.com/v1",
        api_key="",
        model_name="gpt-4o",
        is_active=False,
        config_json='{"temperature": 0.7, "max_tokens": 4096}',
        created_at=now,
        updated_at=now,
    ))

    # Embedding config — use DeepSeek endpoint if available, else OpenAI reference
    if settings.DEEPSEEK_AUTH_TOKEN:
        db.add(ModelConfig(
            name="DeepSeek Embedding (默认)",
            provider="deepseek",
            model_type="embedding",
            endpoint=settings.DEEPSEEK_BASE_URL.rstrip("/") + "/v1",
            api_key=settings.DEEPSEEK_AUTH_TOKEN,
            model_name=settings.DEEPSEEK_MODEL_NAME,
            is_active=True,
            config_json='{"dimensions": 1536}',
            created_at=now,
            updated_at=now,
        ))
    else:
        db.add(ModelConfig(
            name="OpenAI Embedding (默认)",
            provider="openai",
            model_type="embedding",
            endpoint="https://api.openai.com/v1",
            api_key="",
            model_name="text-embedding-3-small",
            is_active=False,
            config_json='{"dimensions": 1536}',
            created_at=now,
            updated_at=now,
        ))

    db.commit()
