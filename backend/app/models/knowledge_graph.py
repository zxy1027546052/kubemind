"""故障知识图谱模型 — 实体与关系存储，支撑图查询与根因推理."""

from datetime import datetime

from sqlalchemy import DateTime, Float, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class KnowledgeEntity(Base):
    """知识图谱实体 — 表示运维领域中的一个具体对象.

    实体类型: k8s_cluster / k8s_node / k8s_namespace / k8s_pod /
    k8s_deployment / k8s_service / alert / anomaly / case / runbook /
    diagnosis_session.
    """

    __tablename__ = "knowledge_entities"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    """主键"""

    label: Mapped[str] = mapped_column(String(200), nullable=False)
    """实体标签 (显示名称)"""

    entity_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    """实体类型: k8s_pod / k8s_node / alert / case / runbook 等"""

    external_id: Mapped[str | None] = mapped_column(String(200), nullable=True, index=True)
    """外部系统 ID，关联到源表主键"""

    properties: Mapped[str] = mapped_column(Text, default="{}")
    """扩展属性 (JSON object)"""

    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=func.now(),
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=func.now(), onupdate=func.now(),
    )


class KnowledgeRelationship(Base):
    """知识图谱关系 — 连接两个实体的有向边.

    关系类型: BELONGS_TO / CONTAINS / TRIGGERED_BY / CAUSES /
    MITIGATES / DIAGNOSES / REFERENCES.
    """

    __tablename__ = "knowledge_relationships"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    """主键"""

    source_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    """源实体 ID (subject)"""

    target_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    """目标实体 ID (object)"""

    relation_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    """关系类型"""

    weight: Mapped[float] = mapped_column(Float, default=1.0)
    """关系权重 (0-1)，用于排序和推理"""

    properties: Mapped[str] = mapped_column(Text, default="{}")
    """扩展属性 (JSON object)"""

    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=func.now(),
    )
