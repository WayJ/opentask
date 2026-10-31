"""知识 SQLAlchemy 模型"""
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Integer,
    String,
    Text,
    Index,
    ForeignKey,
    Table,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from opentask.models.base import DBModel as Base
from opentask.models.knowledge.enums import KnowledgeStatus, KnowledgeVisibility

if TYPE_CHECKING:
    from opentask.models.knowledge_base.model import KnowledgeBase
    from opentask.models.knowledge_category.model import KnowledgeCategory
    # ============================================================================
    # ⚠️ Tag 功能已移除 - 知识库不再需要 tag 功能
    # from opentask.models.tag.model import Tag
    # ============================================================================


def generate_uuid() -> str:
    """生成 UUID"""
    return str(uuid.uuid4())


# ============================================================================
# ⚠️ Tag 功能已移除 - 知识库不再需要 tag 功能
# 知识-标签关联表（多对多关系）
# knowledge_tags = Table(
#     "knowledge_tags",
#     Base.metadata,
#     Column("id", Integer, primary_key=True, autoincrement=True),
#     Column("knowledge_id", String(36), ForeignKey("knowledge.id", ondelete="CASCADE"), nullable=False),
#     Column("tag_id", Integer, ForeignKey("tags.id", ondelete="CASCADE"), nullable=False),
#     Column("created_at", DateTime, insert_default=datetime.utcnow, nullable=False),
#     Index("idx_knowledge_tags_knowledge", "knowledge_id"),
#     Index("idx_knowledge_tags_tag", "tag_id"),
# )
# ============================================================================


class Knowledge(Base):
    """知识模型"""

    __tablename__ = "knowledge"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, insert_default=generate_uuid)
    knowledge_base_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("knowledge_bases.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    content_html: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    category_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("knowledge_categories.id", ondelete="SET NULL"), nullable=True
    )
    status: Mapped[KnowledgeStatus] = mapped_column(
        String(20), insert_default=KnowledgeStatus.DRAFT, nullable=False, index=True
    )
    visibility: Mapped[KnowledgeVisibility] = mapped_column(
        String(20), insert_default=KnowledgeVisibility.INTERNAL, nullable=False
    )
    version: Mapped[int] = mapped_column(Integer, insert_default=1, nullable=False)
    view_count: Mapped[int] = mapped_column(Integer, insert_default=0, nullable=False)
    like_count: Mapped[int] = mapped_column(Integer, insert_default=0, nullable=False)
    is_deleted: Mapped[bool] = mapped_column(Boolean, insert_default=False, nullable=False, index=True)

    created_by: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    updated_by: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, insert_default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, insert_default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    # 文件优先架构字段
    file_path: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    file_mtime: Mapped[Optional[float]] = mapped_column(Integer, nullable=True)
    last_synced_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # 关联
    knowledge_base = relationship("KnowledgeBase", back_populates="knowledge_items")
    category = relationship("KnowledgeCategory", back_populates="knowledge_items")
    # ============================================================================
    # ⚠️ Tag 功能已移除 - 知识库不再需要 tag 功能
    # tags = relationship("Tag", secondary="knowledge_tags", back_populates="knowledge_items")
    # ============================================================================

    __table_args__ = (
        Index("idx_knowledge_kb", "knowledge_base_id"),
        Index("idx_knowledge_category", "category_id"),
        Index("idx_knowledge_status", "status"),
        Index("idx_knowledge_visibility", "visibility"),
        Index("idx_knowledge_slug", "slug"),
        Index("idx_knowledge_created_at", "created_at"),
        Index("idx_knowledge_is_deleted", "is_deleted"),
        Index("idx_knowledge_kb_status", "knowledge_base_id", "status", "is_deleted"),
    )
