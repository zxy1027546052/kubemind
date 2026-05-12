"""知识库文档模型 — 运维手册、技术文档等非结构化知识存储."""

from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Document(Base):
    """知识库文档 — 存储运维相关的参考文档、手册和知识条目.

    文档是知识库的基本单元，支持按类型和分类进行检索。
    内容通过 TF-IDF 向量化后参与语义搜索。
    """

    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    """主键"""

    title: Mapped[str] = mapped_column(String(200), nullable=False)
    """文档标题"""

    type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    """文档类型 (Runbook / 技术文档 / 最佳实践 等)"""

    category: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    """分类标签 (slow_sql / io_saturation / network_issue 等)"""

    size: Mapped[str] = mapped_column(String(50), default="-")
    """文档大小 (展示用，如 '2.3KB')"""

    content: Mapped[str] = mapped_column(Text, default="")
    """文档正文，支持全文检索"""

    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=func.now(),
    )
    """创建时间"""

    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=func.now(), onupdate=func.now(),
    )
    """更新时间 (自动维护)"""
