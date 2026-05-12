"""AI 模型配置模型 — 管理 LLM 和 Embedding 模型的连接信息."""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class ModelConfig(Base):
    """AI 模型配置 — 存储大模型和嵌入模型的连接参数.

    支持 OpenAI 兼容协议 (DeepSeek、OpenAI 等)，
    同时管理 LLM (chat) 和 Embedding 两类模型。
    """

    __tablename__ = "model_configs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    """主键"""

    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    """配置名称 (如 'DeepSeek Chat (默认)')"""

    provider: Mapped[str] = mapped_column(String(50), nullable=False)
    """模型提供商: deepseek / openai"""

    model_type: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    """模型类型: llm (大语言模型) / embedding (向量嵌入)"""

    endpoint: Mapped[str] = mapped_column(String(500), default="")
    """API 端点地址 (如 https://api.deepseek.com/v1)"""

    api_key: Mapped[str] = mapped_column(String(500), default="")
    """API 密钥 (服务端存储，前端脱敏展示)"""

    model_name: Mapped[str] = mapped_column(String(100), nullable=False)
    """模型名称 (如 deepseek-chat / gpt-4o)"""

    is_active: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    """是否启用 (同一类型只有一个激活模型生效)"""

    config_json: Mapped[str] = mapped_column(Text, default="{}")
    """附加配置 JSON (temperature / max_tokens / top_p 等)"""

    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=func.now(),
    )
    """创建时间"""

    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=func.now(), onupdate=func.now(),
    )
    """更新时间 (自动维护)"""
