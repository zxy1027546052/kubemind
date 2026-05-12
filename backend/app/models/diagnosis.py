"""智能诊断会话模型 — 存储基于 RAG + LLM 的故障诊断记录."""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class DiagnosisSession(Base):
    """智能诊断会话 — 一次完整的诊断请求与结果记录.

    诊断流程:
    1. 用户提交故障描述 (query_text)
    2. 向量检索匹配相似案例和 Runbook (matched_items)
    3. 调用 LLM 生成结构化诊断报告 (llm_response)
    4. 返回结果，前端展示诊断报告
    """

    __tablename__ = "diagnosis_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    """主键"""

    query_text: Mapped[str] = mapped_column(Text, nullable=False)
    """用户提交的故障描述"""

    matched_items: Mapped[str] = mapped_column(Text, default="[]")
    """向量检索匹配结果 (JSON 数组: source_type / title / score)"""

    llm_response: Mapped[str] = mapped_column(Text, default="")
    """LLM 生成的诊断结果 (JSON: root_causes / steps / impact / runbook_refs)"""

    model_config_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("model_configs.id"), nullable=True,
    )
    """使用的模型配置 ID (外键 -> model_configs.id)"""

    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending", index=True)
    """诊断状态: pending / running / completed / failed"""

    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=func.now(),
    )
    """创建时间"""

    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=func.now(), onupdate=func.now(),
    )
    """更新时间 (自动维护)"""
