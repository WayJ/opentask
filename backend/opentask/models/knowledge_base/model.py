"""知识库 SQLAlchemy 模型"""
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, String, Text, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from opentask.models.base import DBModel as Base
from opentask.models.knowledge_base.enums import KnowledgeBaseStatus

if TYPE_CHECKING:
    from opentask.models.knowledge.model import Knowledge
    from opentask.models.requirement.model import Project


def generate_uuid() -> str:
    """生成 UUID"""
    return str(uuid.uuid4())


class KnowledgeBase(Base):
    """知识库模型 - 独立的知识管理实体"""

    __tablename__ = "knowledge_bases"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, insert_default=generate_uuid)
    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    icon: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    repository_url: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    status: Mapped[KnowledgeBaseStatus] = mapped_column(
        String(20), insert_default=KnowledgeBaseStatus.ACTIVE, nullable=False, index=True
    )

    # 元数据
    created_at: Mapped[datetime] = mapped_column(DateTime, insert_default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, insert_default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    # 文件优先架构字段
    file_path: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # 部门归属快照
    dept_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("department.id"), nullable=True, index=True,
        comment="部门归属快照（创建时所属部门）"
    )

    # 关联
    knowledge_items = relationship(
        "Knowledge", back_populates="knowledge_base", cascade="all, delete-orphan"
    )
    projects = relationship(
        "Project",
        secondary="project_knowledge_bases",
        back_populates="knowledge_bases",
    )

    __table_args__ = (
        Index("idx_knowledge_bases_status", "status"),
        Index("idx_knowledge_bases_created_at", "created_at"),
        Index("idx_knowledge_bases_name", "name"),
    )
