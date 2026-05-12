"""运维工作流模型 — 定义标准化故障响应的分步流程."""

from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Workflow(Base):
    """运维工作流 — 面向故障场景的标准化分步操作流程.

    工作流将故障响应过程拆分为有序步骤，每步包含操作指令和详细说明。
    可用于事故响应、发布回滚、变更管理等场景。
    """

    __tablename__ = "workflows"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    """主键"""

    title: Mapped[str] = mapped_column(String(200), nullable=False)
    """工作流名称 (如 '数据库故障应急响应流程')"""

    description: Mapped[str] = mapped_column(Text, default="")
    """工作流说明 (适用场景、前置条件)"""

    category: Mapped[str] = mapped_column(String(100), default="", index=True)
    """分类: database / kubernetes / deployment"""

    steps: Mapped[str] = mapped_column(Text, default="[]")
    """步骤列表 (JSON 数组: [{"order": 1, "action": "...", "detail": "..."}])"""

    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="draft", index=True,
    )
    """工作流状态: draft / active / archived"""

    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=func.now(),
    )
    """创建时间"""

    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=func.now(), onupdate=func.now(),
    )
    """更新时间 (自动维护)"""
