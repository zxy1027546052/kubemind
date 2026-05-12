from pathlib import Path

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

    # Vector DB (Milvus)
    VECTOR_DB_TYPE: str = "milvus"
    VECTOR_DB_HOST: str = ""
    VECTOR_DB_PORT: int = 19530
    VECTOR_DB_USER: str = "root"
    VECTOR_DB_PASSWORD: str = ""
    VECTOR_DB_COLLECTION_NAME: str = "kubemind_docs"

    model_config = {
        "env_file": str(_config_dir / ".env"),
        "env_file_encoding": "utf-8",
    }


settings = Settings()
