from pathlib import Path

from pydantic_settings import BaseSettings

_config_dir = Path(__file__).resolve().parent.parent / "config"


class Settings(BaseSettings):
    DATABASE_URL: str = "sqlite:///./data/kubemind.db"
    CORS_ORIGINS: list[str] = ["http://127.0.0.1:5173", "http://localhost:5173"]
    LOG_LEVEL: str = "INFO"
    DEBUG: bool = True
    APP_TITLE: str = "KubeMind Backend"
    APP_VERSION: str = "0.2.0"

    model_config = {
        "env_file": str(_config_dir / ".env"),
        "env_file_encoding": "utf-8",
    }


settings = Settings()
