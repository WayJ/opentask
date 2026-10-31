"""AccessToken SQLAlchemy 模型"""
from datetime import datetime
from sqlalchemy import String, Text, DateTime, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from opentask.models.base import DBModel, UUIDMixin


class AccessToken(DBModel, UUIDMixin, kw_only=True):
    """用户 Access Token 模型"""
    __tablename__ = "access_tokens"

    # 索引
    __table_args__ = (
        Index("idx_access_tokens_user_id", "user_id"),
        Index("idx_access_tokens_token_hash", "token_hash", unique=True),
    )

    # 用户 ID（外键）
    user_id: Mapped[str] = mapped_column(
        "user_id",
        String(36),
        ForeignKey("user.id", ondelete="CASCADE"),
        nullable=False,
        comment="用户 ID"
    )

    # Token 名称
    name: Mapped[str] = mapped_column(
        "name",
        String(255),
        nullable=False,
        comment="Token 名称"
    )

    # Token 描述
    description: Mapped[str | None] = mapped_column(
        "description",
        Text,
        nullable=True,
        comment="Token 描述"
    )

    # Token SHA-256 哈希（不存原文）
    token_hash: Mapped[str] = mapped_column(
        "token_hash",
        String(64),
        nullable=False,
        comment="Token SHA-256 哈希"
    )

    # Token 前缀（用于展示，如 vk_a1b2c3d4）
    token_prefix: Mapped[str] = mapped_column(
        "token_prefix",
        String(12),
        nullable=False,
        comment="Token 前缀"
    )

    # 过期时间
    expires_at: Mapped[datetime] = mapped_column(
        "expires_at",
        DateTime,
        nullable=False,
        comment="过期时间"
    )

    # 最后使用时间
    last_used_at: Mapped[datetime | None] = mapped_column(
        "last_used_at",
        DateTime,
        nullable=True,
        comment="最后使用时间"
    )

    # 创建时间
    created_at: Mapped[datetime] = mapped_column(
        "created_at",
        DateTime,
        nullable=False,
        comment="创建时间"
    )

    # 更新时间
    updated_at: Mapped[datetime] = mapped_column(
        "updated_at",
        DateTime,
        nullable=False,
        comment="更新时间"
    )

    # 关系
    user: Mapped["UserModel"] = relationship("UserModel", back_populates="access_tokens")

    def __repr__(self) -> str:
        return f"<AccessToken(id={self.id!r}, user_id={self.user_id!r}, name={self.name!r}, prefix={self.token_prefix!r})>"
