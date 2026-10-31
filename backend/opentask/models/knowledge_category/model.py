"""知识分类 SQLAlchemy 模型"""
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Column, DateTime, Integer, String, Index, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from opentask.models.base import DBModel as Base

if TYPE_CHECKING:
    from opentask.models.knowledge.model import Knowledge


class KnowledgeCategory(Base):
    """知识分类模型（树形结构）"""

    __tablename__ = "knowledge_categories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    icon: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, insert_default=0, nullable=False)
    parent_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("knowledge_categories.id", ondelete="CASCADE"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, insert_default=datetime.utcnow, nullable=False)

    # 自引用关系（树形结构）
    children = relationship(
        "KnowledgeCategory",
        back_populates="parent",
        remote_side=[id],
        cascade="all, delete",
    )
    parent = relationship("KnowledgeCategory", back_populates="children")
    knowledge_items = relationship("Knowledge", back_populates="category")

    __table_args__ = (
        Index("idx_categories_parent", "parent_id"),
        Index("idx_categories_sort", "sort_order"),
    )
