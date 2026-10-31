"""Issue Collection 数据模型"""
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, List, Optional
from sqlalchemy import String, Integer, Text, ForeignKey, DateTime, JSON, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.mysql import ENUM

from opentask.models.base import DBModel
from .enums import CollectionStatus


if TYPE_CHECKING:
    from opentask.models.user.model import UserModel
    from opentask.models.issue.model import Issue


def generate_uuid() -> str:
    """生成 UUID"""
    return str(uuid.uuid4())


class IssueCollection(DBModel):
    """问题集主模型"""
    __tablename__ = "issue_collections"

    # 主键
    id: Mapped[str] = mapped_column(String(36), primary_key=True, insert_default=generate_uuid)

    # 基本信息
    title: Mapped[str] = mapped_column(String(255), nullable=False, comment="问题集标题")
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="问题描述（Markdown 格式）")

    # 状态
    status: Mapped[str] = mapped_column(
        ENUM("pending", "in_progress", "completed", name="collection_status"),
        nullable=False,
        insert_default="pending",
        comment="状态"
    )

    # 关联的 Issue ID 列表
    issue_ids: Mapped[List[str]] = mapped_column(
        JSON,
        nullable=False,
        comment="关联的 Issue ID 列表"
    )

    # 创建人
    creator_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
        comment="创建人 ID"
    )

    # 时间戳
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        insert_default=datetime.now,
        comment="创建时间"
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        insert_default=datetime.now,
        onupdate=datetime.now,
        comment="更新时间"
    )

    # 索引
    __table_args__ = (
        Index('idx_collection_status', 'status'),
        Index('idx_collection_created_at', 'created_at'),
        Index('idx_collection_creator', 'creator_id'),
    )

    # 关系
    creator: Mapped["UserModel"] = relationship(
        "UserModel",
        foreign_keys=[creator_id],
        primaryjoin="IssueCollection.creator_id == UserModel.id",
        lazy="select"
    )
