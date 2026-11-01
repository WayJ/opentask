"""OAuth2 Provider 数据模型（client / 授权码 / access token / refresh token）

设计要点（见 docs/superpowers/specs/2026-11-02-oauth2-provider-design.md）：

- client_secret / 授权码 / refresh token **一律只存 SHA-256 哈希**，明文仅在响应里下发一次；
- access token 本身是 JWT（复用 opentask.jwt_utils），本表只登记其 jti 哈希，
  用于吊销与「已签发」审计，不做每次请求的查表校验（校验走签名 + jti 黑名单）；
- refresh token 与 Web 会话的 refresh_token（refresh_token 表）**生命周期独立**：
  Web 会话改密不应吊销第三方应用授权，反之亦然，故另立本表；
- scope 列存空格分隔的 scope 串（**不是 scp**——scp 已被 OpenTask 内部
  受限令牌 pwd_change 占用，语义互斥）。
"""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from opentask.models.base import DBModel, UUIDMixin


class OAuthClient(DBModel, UUIDMixin, kw_only=True):
    """OAuth 客户端注册行（授权服务器侧的 client 登记）"""

    __tablename__ = "oauth_clients"

    __table_args__ = (
        Index(None, "client_id", unique=True),
        Index(None, "created_by"),
    )

    # 公开客户端标识（授权请求里出现，非机密）
    client_id: Mapped[str] = mapped_column(
        "client_id",
        String(64),
        nullable=False,
        comment="客户端公开标识",
    )

    # 客户端密钥 SHA-256 十六进制哈希（不存原文）
    client_secret_hash: Mapped[str] = mapped_column(
        "client_secret_hash",
        String(64),
        nullable=False,
        comment="客户端密钥 SHA-256 哈希",
    )

    # 密钥前缀（仅供管理界面展示与定位，如 "cs_ab12"）
    client_secret_prefix: Mapped[str] = mapped_column(
        "client_secret_prefix",
        String(16),
        nullable=False,
        comment="客户端密钥前缀（展示用）",
    )

    # 应用名（同意页展示）
    name: Mapped[str] = mapped_column(
        "name",
        String(255),
        nullable=False,
        comment="应用名称",
    )

    # 应用描述（同意页展示）
    description: Mapped[str | None] = mapped_column(
        "description",
        Text,
        nullable=True,
        comment="应用描述",
    )

    # 回调地址白名单（逗号分隔，授权时精确匹配，防开放重定向）
    redirect_uris: Mapped[str] = mapped_column(
        "redirect_uris",
        Text,
        nullable=False,
        comment="回调地址白名单（逗号分隔）",
    )

    # 允许的 scope 集合（空格分隔）
    scopes: Mapped[str] = mapped_column(
        "scopes",
        String(512),
        nullable=False,
        default="",
        comment="允许的 scope 集合（空格分隔）",
    )

    # 允许的 grant_type（空格分隔）
    grant_types: Mapped[str] = mapped_column(
        "grant_types",
        String(128),
        nullable=False,
        default="authorization_code refresh_token",
        comment="允许的授权类型（空格分隔）",
    )

    # 状态：ACTIVE / DISABLED
    status: Mapped[str] = mapped_column(
        "status",
        String(16),
        nullable=False,
        default="ACTIVE",
        comment="状态 ACTIVE/DISABLED",
    )

    # 注册人（用户 ID，外键级联删除）
    created_by: Mapped[str] = mapped_column(
        "created_by",
        String(36),
        ForeignKey("user.id", ondelete="CASCADE"),
        nullable=False,
        comment="注册人用户 ID",
    )

    created_at: Mapped[datetime] = mapped_column(
        "created_at",
        DateTime,
        nullable=False,
        comment="创建时间",
    )

    updated_at: Mapped[datetime] = mapped_column(
        "updated_at",
        DateTime,
        nullable=False,
        comment="更新时间",
    )


class OAuthAuthorizationCode(DBModel, UUIDMixin, kw_only=True):
    """授权码（只存 SHA-256 哈希；一次性消费，10 分钟 TTL）"""

    __tablename__ = "oauth_authorization_codes"

    __table_args__ = (
        Index(None, "code_hash", unique=True),
        Index(None, "client_id"),
        Index(None, "user_id"),
    )

    # 授权码 SHA-256 哈希（不存原文）
    code_hash: Mapped[str] = mapped_column(
        "code_hash",
        String(64),
        nullable=False,
        comment="授权码 SHA-256 哈希",
    )

    # 所属客户端
    client_id: Mapped[str] = mapped_column(
        "client_id",
        String(64),
        ForeignKey("oauth_clients.client_id", ondelete="CASCADE"),
        nullable=False,
        comment="客户端标识",
    )

    # 授权用户
    user_id: Mapped[str] = mapped_column(
        "user_id",
        String(36),
        ForeignKey("user.id", ondelete="CASCADE"),
        nullable=False,
        comment="授权用户 ID",
    )

    # 实际使用的回调地址（换 token 时须与之一致）
    redirect_uri: Mapped[str] = mapped_column(
        "redirect_uri",
        String(2048),
        nullable=False,
        comment="回调地址",
    )

    # 授予的 scope（空格分隔）
    scope: Mapped[str] = mapped_column(
        "scope",
        String(512),
        nullable=False,
        default="",
        comment="授予的 scope（空格分隔）",
    )

    # 过期时间（默认签发后 10 分钟）
    expires_at: Mapped[datetime] = mapped_column(
        "expires_at",
        DateTime,
        nullable=False,
        comment="过期时间",
    )

    # 消费时间（非空即已用过；二次使用视为重放）
    used_at: Mapped[datetime | None] = mapped_column(
        "used_at",
        DateTime,
        nullable=True,
        comment="消费时间（一次性）",
    )

    created_at: Mapped[datetime] = mapped_column(
        "created_at",
        DateTime,
        nullable=False,
        comment="创建时间",
    )


class OAuthAccessToken(DBModel, UUIDMixin, kw_only=True):
    """已签发的 access token 登记行（JWT 本身不落库；此处只登记 jti 哈希）"""

    __tablename__ = "oauth_access_tokens"

    __table_args__ = (
        Index(None, "token_hash", unique=True),
        Index(None, "client_id"),
        Index(None, "user_id"),
    )

    # JWT jti 的 SHA-256 哈希（不存原文）
    token_hash: Mapped[str] = mapped_column(
        "token_hash",
        String(64),
        nullable=False,
        comment="access token jti 的 SHA-256 哈希",
    )

    # 所属客户端
    client_id: Mapped[str] = mapped_column(
        "client_id",
        String(64),
        ForeignKey("oauth_clients.client_id", ondelete="CASCADE"),
        nullable=False,
        comment="客户端标识",
    )

    # 代表用户
    user_id: Mapped[str] = mapped_column(
        "user_id",
        String(36),
        ForeignKey("user.id", ondelete="CASCADE"),
        nullable=False,
        comment="代表用户 ID",
    )

    # 授予的 scope（空格分隔）
    scope: Mapped[str] = mapped_column(
        "scope",
        String(512),
        nullable=False,
        default="",
        comment="授予的 scope（空格分隔）",
    )

    # 过期时间
    expires_at: Mapped[datetime] = mapped_column(
        "expires_at",
        DateTime,
        nullable=False,
        comment="过期时间",
    )

    # 吊销时间（非空即失效）
    revoked_at: Mapped[datetime | None] = mapped_column(
        "revoked_at",
        DateTime,
        nullable=True,
        comment="吊销时间",
    )

    created_at: Mapped[datetime] = mapped_column(
        "created_at",
        DateTime,
        nullable=False,
        comment="创建时间",
    )


class OAuthRefreshToken(DBModel, UUIDMixin, kw_only=True):
    """OAuth refresh token（只存 SHA-256 哈希；轮换 + 重放即吊销该用户全部 token）"""

    __tablename__ = "oauth_refresh_tokens"

    __table_args__ = (
        Index(None, "token_hash", unique=True),
        Index(None, "client_id"),
        Index(None, "user_id"),
    )

    # refresh token 明文的 SHA-256 哈希（不存原文）
    token_hash: Mapped[str] = mapped_column(
        "token_hash",
        String(64),
        nullable=False,
        comment="refresh token SHA-256 哈希",
    )

    # 所属客户端
    client_id: Mapped[str] = mapped_column(
        "client_id",
        String(64),
        ForeignKey("oauth_clients.client_id", ondelete="CASCADE"),
        nullable=False,
        comment="客户端标识",
    )

    # 代表用户
    user_id: Mapped[str] = mapped_column(
        "user_id",
        String(36),
        ForeignKey("user.id", ondelete="CASCADE"),
        nullable=False,
        comment="代表用户 ID",
    )

    # 授予的 scope（空格分隔）
    scope: Mapped[str] = mapped_column(
        "scope",
        String(512),
        nullable=False,
        default="",
        comment="授予的 scope（空格分隔）",
    )

    # 过期时间
    expires_at: Mapped[datetime] = mapped_column(
        "expires_at",
        DateTime,
        nullable=False,
        comment="过期时间",
    )

    # 吊销时间（非空即失效；被再次使用视为重放）
    revoked_at: Mapped[datetime | None] = mapped_column(
        "revoked_at",
        DateTime,
        nullable=True,
        comment="吊销时间",
    )

    # 轮换后的新 token 哈希（便于排查轮换链）
    rotated_to_hash: Mapped[str | None] = mapped_column(
        "rotated_to_hash",
        String(64),
        nullable=True,
        comment="轮换后的新 token 哈希",
    )

    created_at: Mapped[datetime] = mapped_column(
        "created_at",
        DateTime,
        nullable=False,
        comment="创建时间",
    )
