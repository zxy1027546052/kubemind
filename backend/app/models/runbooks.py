"""应急处置手册模型 — 标准化运维操作流程，支撑故障快速恢复."""

from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Runbook(Base):
    """应急处置手册 — 针对特定故障场景的标准化操作指南.

    每本 Runbook 面向一个明确的故障场景，包含触发条件、操作步骤、
    风险提示和回滚方案。在智能诊断中，匹配到的 Runbook 会作为
    推荐的处置参考反馈给用户。
    """

    __tablename__ = "runbooks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    """主键"""

    title: Mapped[str] = mapped_column(String(200), nullable=False)
    """手册标题 (描述处置场景)"""

    scenario: Mapped[str] = mapped_column(Text, default="")
    """触发场景 (什么条件下应启用本手册)"""

    steps: Mapped[str] = mapped_column(Text, default="")
    """操作步骤 (按顺序执行的具体命令和检查项)"""

    risk: Mapped[str] = mapped_column(Text, default="")
    """风险提示 (执行过程中可能引入的副作用)"""

    rollback: Mapped[str] = mapped_column(Text, default="")
    """回滚方案 (操作失败或引入新问题时的恢复步骤)"""

    category: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    """分类 (slow_sql / io_saturation / network_issue 等)"""

    tags: Mapped[str] = mapped_column(String(500), default="")
    """标签，逗号分隔 (用于辅助检索)"""

    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=func.now(),
    )
    """创建时间"""

    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=func.now(), onupdate=func.now(),
    )
    """更新时间 (自动维护)"""
