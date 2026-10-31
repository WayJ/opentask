"""项目-知识库关联 SQLAlchemy 模型"""
import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, String, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column

from opentask.models.base import DBModel as Base


def generate_uuid() -> str:
    """生成 UUID"""
    import uuid

    return str(uuid.uuid4())


class ProjectKnowledgeBase(Base):
    """项目-知识库关联模型（多对多）"""

    __tablename__ = "project_knowledge_bases"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, insert_default=generate_uuid)
    project_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    knowledge_base_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("knowledge_bases.id", ondelete="CASCADE"), nullable=False, index=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, insert_default=datetime.utcnow, nullable=False)

    __table_args__ = (
        Index("idx_project_kb_project", "project_id"),
        Index("idx_project_kb_kb", "knowledge_base_id"),
        Index("uq_project_kb", "project_id", "knowledge_base_id", unique=True),
    )
