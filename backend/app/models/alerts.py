"""告警模型 — 管理来自 Prometheus、K8s 等多源告警事件."""

from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Alert(Base):
    """告警事件 — 记录来自各监控系统的告警及处置状态.

    告警是整个运维工作台的关键入口，按严重等级、状态和分类
    进行多维筛选，支持告警确认 (ACK) 和解决流转。
    """

    __tablename__ = "alerts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    """主键"""

    title: Mapped[str] = mapped_column(String(200), nullable=False)
    """告警标题 (简述告警内容)"""

    description: Mapped[str] = mapped_column(Text, default="")
    """告警详情 (详细描述、影响范围)"""

    severity: Mapped[str] = mapped_column(
        String(20), nullable=False, default="medium", index=True,
    )
    """严重等级: critical / high / medium / low"""

    source: Mapped[str] = mapped_column(String(100), default="manual")
    """告警来源: prometheus / kubernetes / node_exporter / manual 等"""

    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="active", index=True,
    )
    """告警状态: active / acknowledged / resolved"""

    assigned_to: Mapped[str] = mapped_column(String(100), default="")
    """指派处理人"""

    category: Mapped[str] = mapped_column(String(100), default="", index=True)
    """分类: database / kubernetes / infrastructure / security 等"""

    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=func.now(),
    )
    """创建时间"""

    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=func.now(), onupdate=func.now(),
    )
    """更新时间 (自动维护)"""
