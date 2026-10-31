"""文档模块 SQLAlchemy 模型"""
import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    Column,
    DateTime,
    String,
    Text,
    Integer,
    Boolean,
    ForeignKey,
    Enum as SQLEnum,
    Index,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from opentask.models.base import DBModel as Base
from opentask.models.document.enums import DocumentStatus

if TYPE_CHECKING:
    from opentask.models.user.model import User


def generate_uuid() -> str:
    """生成 UUID"""
    return str(uuid.uuid4())


class Document(Base):
    """文档模型 - 简化的附件模型，Document = Attachment

    文档就是附件，支持多种文件类型（图片、PDF、Word 等）。
    只存储文件元数据，实际文件存储在本地文件系统。
    """
    __tablename__ = "documents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, insert_default=generate_uuid)

    # 多态关联 - 支持关联任何实体（requirement, task, project, repo 等）
    entity_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
        comment="实体类型 (requirement/task/project/repo 等)"
    )
    entity_id: Mapped[str] = mapped_column(
        String(36),
        nullable=False,
        index=True,
        comment="实体 ID"
    )

    # 文件信息（必需）
    file_path: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
        comment="文件存储路径（相对路径）"
    )
    file_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="原始文件名"
    )
    file_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="MIME 类型"
    )
    file_size: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="文件大小（字节）"
    )

    # 状态
    status: Mapped[DocumentStatus] = mapped_column(
        SQLEnum(DocumentStatus),
        insert_default=DocumentStatus.DRAFT,
        nullable=False,
    )

    # 元数据
    created_at: Mapped[datetime] = mapped_column(DateTime, insert_default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, insert_default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )
    created_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    updated_by: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # 部门归属快照
    dept_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("department.id"),
        nullable=True,
        index=True,
        comment="部门归属快照（创建时所属部门）"
    )

    __table_args__ = (
        Index("idx_documents_entity", "entity_type", "entity_id"),  # 复合索引，提高查询性能
        Index("idx_documents_status", "status"),
        Index("idx_documents_created_at", "created_at"),
        # 唯一约束：同一实体下不能有同名文件（用于文件覆盖逻辑）
        UniqueConstraint('entity_type', 'entity_id', 'file_name', name='uq_document_entity_filename'),
    )

