from datetime import datetime
from sqlalchemy import Boolean, String, Text, Integer, DateTime, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import true, false

from opentask.models.base import DBModel, UUIDMixin


class UserModel(DBModel, UUIDMixin, kw_only=True):
    __tablename__ = "user"

    # ===== 原有字段 =====
    name: Mapped[str] = mapped_column("name", String(100), nullable=True, comment="用户名（保留兼容）")
    # password 明文列已由 2026_10_23_0001 迁移移除，认证统一走 password_hash（bcrypt）

    openai_api_key: Mapped[str | None] = mapped_column("openai_api_key", String(255), nullable=True)
    preferred_openai_model: Mapped[str | None] = mapped_column("preferred_openai_model", String(100), nullable=True)
    langsmith_api_key: Mapped[str | None] = mapped_column("langsmith_api_key", String(255), nullable=True)
    sentry_enabled: Mapped[bool] = mapped_column("sentry_enabled", Boolean, server_default=false())
    analytics_enabled: Mapped[bool] = mapped_column("analytics_enabled", Boolean, server_default=true())
    hide_sql_preference: Mapped[bool] = mapped_column("hide_sql_preference", Boolean, server_default=false())
    openai_base_url: Mapped[str | None] = mapped_column("openai_base_url", String(500), nullable=True)

    # ===== SSO 集成字段 =====
    sso_user_id: Mapped[str | None] = mapped_column(
        "sso_user_id", String(100), nullable=True, unique=True,
        comment="SSO 用户 ID（唯一索引，用于关联 SSO 用户）"
    )
    sso_token: Mapped[str | None] = mapped_column(
        "sso_token", String(2048), nullable=True,
        comment="SSO 登录 token（加密存储，Fernet 格式）"
    )
    sso_account: Mapped[str | None] = mapped_column(
        "sso_account", String(100), nullable=True,
        comment="SSO 账号"
    )
    sso_name: Mapped[str | None] = mapped_column(
        "sso_name", String(100), nullable=True,
        comment="SSO 姓名"
    )
    organize_id: Mapped[str | None] = mapped_column(
        "organize_id", String(100), nullable=True,
        comment="SSO 组织 ID"
    )
    organize_name: Mapped[str | None] = mapped_column(
        "organize_name", String(200), nullable=True,
        comment="SSO 组织名称"
    )
    position_id: Mapped[str | None] = mapped_column(
        "position_id", String(100), nullable=True,
        comment="SSO 岗位 ID"
    )
    position_name: Mapped[str | None] = mapped_column(
        "position_name", String(100), nullable=True,
        comment="SSO 岗位名称"
    )

    # ===== OpenTask JWT Token 字段 =====
    jwt_expires_at: Mapped[datetime | None] = mapped_column(
        "jwt_expires_at", DateTime, nullable=True,
        comment="JWT token 过期时间"
    )

    # ===== 本地账号安全字段 =====
    # 登录用户名（本地认证用，唯一性由索引保证，便于 SQLite ADD COLUMN 迁移）
    username: Mapped[str | None] = mapped_column(
        "username", String(50), nullable=True,
        comment="登录用户名（本地认证）"
    )
    # 密码哈希（bcrypt 等，绝不存明文）
    password_hash: Mapped[str | None] = mapped_column(
        "password_hash", String(255), nullable=True,
        comment="密码哈希"
    )
    # 是否强制下次登录改密
    must_change_password: Mapped[bool] = mapped_column(
        "must_change_password", Boolean, default=False,
        comment="是否强制下次登录修改密码"
    )
    # token 版本号，递增使既有 JWT 全部失效
    token_version: Mapped[int] = mapped_column(
        "token_version", Integer, default=0,
        comment="token 版本号（用于批量吊销 JWT）"
    )
    # 钉钉用户 ID（唯一性由索引保证）
    dingtalk_user_id: Mapped[str | None] = mapped_column(
        "dingtalk_user_id", String(64), nullable=True,
        comment="钉钉用户 ID"
    )
    # 连续登录失败次数
    failed_attempts: Mapped[int] = mapped_column(
        "failed_attempts", Integer, default=0,
        comment="连续登录失败次数"
    )
    # 账号锁定截止时间（NULL 表示未锁定）
    locked_until: Mapped[datetime | None] = mapped_column(
        "locked_until", DateTime, nullable=True,
        comment="账号锁定截止时间"
    )

    # ===== 本地权限管理字段 =====
    status: Mapped[int] = mapped_column(
        "status", Integer, default=1,
        comment="用户状态：1-启用、0-禁用"
    )
    role: Mapped[str] = mapped_column(
        "role", String(50), default="viewer",
        comment="用户角色：admin、maintainer、developer、viewer"
    )

    # ===== 时间字段 =====
    created_at: Mapped[datetime] = mapped_column(
        "created_at", DateTime, insert_default=datetime.utcnow, nullable=False,
        comment="创建时间"
    )
    last_login_time: Mapped[datetime | None] = mapped_column(
        "last_login_time", DateTime, nullable=True,
        comment="最后登录时间"
    )
    sync_time: Mapped[datetime | None] = mapped_column(
        "sync_time", DateTime, nullable=True,
        comment="SSO 信息同步时间"
    )

    # 关系 - 用户的 Access Tokens
    access_tokens: Mapped[list["AccessToken"]] = relationship("AccessToken", back_populates="user", cascade="all, delete-orphan")

    __table_args__ = (
        # 唯一性用表级索引而非列级 unique，兼容 SQLite ADD COLUMN 迁移
        Index("uq_user_username", "username", unique=True),
        Index("uq_user_dingtalk_user_id", "dingtalk_user_id", unique=True),
    )

