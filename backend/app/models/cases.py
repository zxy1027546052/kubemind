"""历史故障案例模型 — 沉淀运维排障经验，支撑 RAG 智能诊断."""

from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Case(Base):
    """历史故障案例 — 记录已解决的线上故障的完整诊断链路.

    案例是智能诊断的核心数据源：向量检索匹配相似故障后，
    将匹配到的案例作为 prompt context 喂给 LLM 生成诊断建议。
    """

    __tablename__ = "cases"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    """主键"""

    title: Mapped[str] = mapped_column(String(200), nullable=False)
    """案例标题 (简述故障现象)"""

    symptom: Mapped[str] = mapped_column(Text, default="")
    """故障现象 (业务侧观测到的异常表现)"""

    root_cause: Mapped[str] = mapped_column(Text, default="")
    """根因分析 (排查后确认的根本原因)"""

    steps: Mapped[str] = mapped_column(Text, default="")
    """排查步骤 (按顺序记录的诊断操作)"""

    impact: Mapped[str] = mapped_column(Text, default="")
    """影响评估 (故障范围、时长、受影响服务)"""

    conclusion: Mapped[str] = mapped_column(Text, default="")
    """复盘结论与改进措施"""

    category: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    """分类 (connection_pool / io_saturation / network_issue 等)"""

    severity: Mapped[str] = mapped_column(String(20), default="medium", index=True)
    """严重等级: critical / high / medium / low"""

    status: Mapped[str] = mapped_column(String(20), default="open", index=True)
    """案例状态: open / resolved / archived"""

    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=func.now(),
    )
    """创建时间"""

    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=func.now(), onupdate=func.now(),
    )
    """更新时间 (自动维护)"""
