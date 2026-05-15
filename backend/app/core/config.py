from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings

_config_dir = Path(__file__).resolve().parent.parent / "config"


class Settings(BaseSettings):
    DATABASE_URL: str = "sqlite:///./data/kubemind.db"
    CORS_ORIGINS: list[str] = ["http://127.0.0.1:5173", "http://localhost:5173"]
    LOG_LEVEL: str = "INFO"
    DEBUG: bool = True
    APP_TITLE: str = "KubeMind Backend"
    APP_VERSION: str = "0.3.0"

    # DeepSeek
    DEEPSEEK_MODEL_NAME: str = "deepseek-chat"
    DEEPSEEK_BASE_URL: str = "https://api.deepseek.com"
    DEEPSEEK_AUTH_TOKEN: str = ""

    # Kubernetes
    KUBECONFIG_PATH: str = "./app/config/kubeconfig.yaml"

    # Observability
    PROMETHEUS_BASE_URL: str = ""
    PROMETHEUS_TIMEOUT_SECONDS: float = 5.0
    LOKI_BASE_URL: str = ""
    LOKI_TIMEOUT_SECONDS: float = 5.0
    OBSERVABILITY_MAX_RANGE_SECONDS: int = 3600
    OBSERVABILITY_MAX_LOG_LINES: int = 200

    # Vector DB (Milvus)
    VECTOR_DB_TYPE: str = "milvus"
    VECTOR_DB_HOST: str = ""
    VECTOR_DB_PORT: int = 19530
    VECTOR_DB_USER: str = "root"
    VECTOR_DB_PASSWORD: str = ""
    VECTOR_DB_COLLECTION_NAME: str = "kubemind_docs"

    @field_validator("DEBUG", mode="before")
    @classmethod
    def parse_debug(cls, value):
        if isinstance(value, bool):
            return value
        if isinstance(value, str) and value.lower() in {"release", "prod", "production"}:
            return False
        return value

    model_config = {
        "env_file": str(_config_dir / ".env"),
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }


settings = Settings()
