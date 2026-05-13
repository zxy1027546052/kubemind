from datetime import datetime

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.model_config import ModelConfig
from app.services.embedding import HASH_EMBEDDING_DIM, HASH_EMBEDDING_MODEL_NAME


def _ensure_local_hash_embedding(db: Session, now: datetime) -> None:
    """保证存在一条 active 的本地哈希 embedding 配置；将错配为 embedding 的
    chat 模型 (如 deepseek-chat) 标为 inactive，避免向量化时撞 404。
    """
    # 把任何 model_type='embedding' 且 model_name 以 '-chat' 结尾的旧记录禁用
    bad = (
        db.query(ModelConfig)
        .filter(ModelConfig.model_type == "embedding")
        .filter(ModelConfig.model_name.like("%-chat"))
        .all()
    )
    for row in bad:
        row.is_active = False
        row.updated_at = now

    local = (
        db.query(ModelConfig)
        .filter(ModelConfig.model_name == HASH_EMBEDDING_MODEL_NAME)
        .first()
    )
    if local is None:
        db.add(ModelConfig(
            name="Local Hash Embedding (离线兜底)",
            provider="local",
            model_type="embedding",
            endpoint="",
            api_key="",
            model_name=HASH_EMBEDDING_MODEL_NAME,
            is_active=True,
            config_json=f'{{"dimensions": {HASH_EMBEDDING_DIM}}}',
            created_at=now,
            updated_at=now,
        ))
    else:
        local.is_active = True
        local.updated_at = now


def seed_model_configs(db: Session) -> None:
    now = datetime.now()

    if not db.query(ModelConfig).first():
        # DeepSeek LLM
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

        # OpenAI LLM (备用)
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

        # OpenAI Embedding (备用，需用户配置 api_key)
        db.add(ModelConfig(
            name="OpenAI Embedding (备用)",
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

    # 总是幂等执行：保证本地哈希 embedding 是 active，禁用错配的 chat→embedding
    _ensure_local_hash_embedding(db, now)
    db.commit()
