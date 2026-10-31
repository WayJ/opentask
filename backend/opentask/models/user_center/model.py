"""用户中心数据模型（部门/岗位/角色/权限/刷新令牌）

共 9 张表：department, position, user_dept, role, permission,
role_permission, user_role, role_dept, refresh_token。

约定：
- 全部继承 DBModel（kw_only dataclass），单主键表混入 UUIDMixin；
- 外键只建列不做 relationship（避免 greenlet 异步问题，见 rd_group 先例）；
- data_scope 用 String(20) 而非 ENUM，保证 SQLite 可建表；
- user 表在 models/user 模块，通过全量 import opentask.models 注册后
  以字符串 "user.id" 引用（与 access_token 写法一致）。
"""
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, SmallInteger, String, quoted_name
from sqlalchemy.orm import Mapped, mapped_column

from opentask.models.base import DBModel, UUIDMixin


class Department(DBModel, UUIDMixin, kw_only=True):
    """部门（树形，物化路径）"""
    __tablename__ = "department"

    # 父部门，根部门为 NULL
    parent_id: Mapped[str | None] = mapped_column(
        "parent_id",
        String(36),
        ForeignKey("department.id"),
        nullable=True,
        comment="父部门 ID，根为 NULL",
    )

    # 部门名称
    name: Mapped[str] = mapped_column(
        "name",
        String(100),
        nullable=False,
        comment="部门名称",
    )

    # 物化路径，如 /root/dept-a/dept-b
    path: Mapped[str] = mapped_column(
        "path",
        String(500),
        nullable=False,
        index=True,
        comment="物化路径",
    )

    # 排序号
    sort: Mapped[int] = mapped_column(
        "sort",
        Integer,
        nullable=False,
        insert_default=0,
        comment="排序号",
    )

    # 状态：1 启用 0 禁用
    status: Mapped[int] = mapped_column(
        "status",
        SmallInteger,
        nullable=False,
        insert_default=1,
        comment="状态：1 启用 0 禁用",
    )

    # 钉钉部门 ID 映射
    dingtalk_dept_id: Mapped[str | None] = mapped_column(
        "dingtalk_dept_id",
        String(64),
        nullable=True,
        unique=True,
        comment="钉钉部门 ID",
    )

    created_at: Mapped[datetime] = mapped_column(
        "created_at",
        DateTime,
        nullable=False,
        insert_default=datetime.utcnow,
        comment="创建时间",
    )
    updated_at: Mapped[datetime] = mapped_column(
        "updated_at",
        DateTime,
        nullable=False,
        insert_default=datetime.utcnow,
        onupdate=datetime.utcnow,
        comment="更新时间",
    )


class Position(DBModel, UUIDMixin, kw_only=True):
    """岗位"""
    # position 是 SQL 关键字（POSITION 函数），显式加引号避免方言不转义导致建表失败
    __tablename__ = quoted_name("position", True)

    # 岗位名称
    name: Mapped[str] = mapped_column(
        "name",
        String(100),
        nullable=False,
        comment="岗位名称",
    )

    # 钉钉岗位 ID 映射
    dingtalk_job_id: Mapped[str | None] = mapped_column(
        "dingtalk_job_id",
        String(64),
        nullable=True,
        unique=True,
        comment="钉钉岗位 ID",
    )

    created_at: Mapped[datetime] = mapped_column(
        "created_at",
        DateTime,
        nullable=False,
        insert_default=datetime.utcnow,
        comment="创建时间",
    )
    updated_at: Mapped[datetime] = mapped_column(
        "updated_at",
        DateTime,
        nullable=False,
        insert_default=datetime.utcnow,
        onupdate=datetime.utcnow,
        comment="更新时间",
    )


class UserDept(DBModel, kw_only=True):
    """用户-部门多对多关联（复合主键 user_id + dept_id）"""
    __tablename__ = "user_dept"

    # 用户 ID
    user_id: Mapped[str] = mapped_column(
        "user_id",
        String(36),
        ForeignKey("user.id", ondelete="CASCADE"),
        primary_key=True,
        comment="用户 ID",
    )

    # 部门 ID
    dept_id: Mapped[str] = mapped_column(
        "dept_id",
        String(36),
        ForeignKey("department.id", ondelete="CASCADE"),
        primary_key=True,
        comment="部门 ID",
    )

    # 是否主部门（每用户仅一行为 true，应用层保证）
    is_primary: Mapped[bool] = mapped_column(
        "is_primary",
        Boolean,
        nullable=False,
        insert_default=False,
        comment="是否主部门",
    )

    # 岗位 ID，nullable
    position_id: Mapped[str | None] = mapped_column(
        "position_id",
        String(36),
        ForeignKey("position.id"),
        nullable=True,
        comment="岗位 ID",
    )


class Role(DBModel, UUIDMixin, kw_only=True):
    """角色"""
    __tablename__ = "role"

    # 角色编码，如 admin/maintainer/developer/viewer
    code: Mapped[str] = mapped_column(
        "code",
        String(50),
        nullable=False,
        unique=True,
        comment="角色编码",
    )

    # 角色名称
    name: Mapped[str] = mapped_column(
        "name",
        String(100),
        nullable=False,
        comment="角色名称",
    )

    # 描述
    description: Mapped[str | None] = mapped_column(
        "description",
        String(255),
        nullable=True,
        comment="角色描述",
    )

    # 数据范围：ALL / DEPT_AND_CHILD / DEPT / SELF / CUSTOM
    # 用 String 而非 ENUM，保证 SQLite 可建表
    data_scope: Mapped[str] = mapped_column(
        "data_scope",
        String(20),
        nullable=False,
        insert_default="SELF",
        comment="数据范围：ALL/DEPT_AND_CHILD/DEPT/SELF/CUSTOM",
    )

    # 是否系统预置角色（不可删除）
    is_system: Mapped[bool] = mapped_column(
        "is_system",
        Boolean,
        nullable=False,
        insert_default=False,
        comment="是否系统预置角色",
    )

    # 状态：1 启用 0 禁用
    status: Mapped[int] = mapped_column(
        "status",
        SmallInteger,
        nullable=False,
        insert_default=1,
        comment="状态：1 启用 0 禁用",
    )

    created_at: Mapped[datetime] = mapped_column(
        "created_at",
        DateTime,
        nullable=False,
        insert_default=datetime.utcnow,
        comment="创建时间",
    )
    updated_at: Mapped[datetime] = mapped_column(
        "updated_at",
        DateTime,
        nullable=False,
        insert_default=datetime.utcnow,
        onupdate=datetime.utcnow,
        comment="更新时间",
    )


class Permission(DBModel, UUIDMixin, kw_only=True):
    """权限点字典（代码播种），如 manage:user:create"""
    __tablename__ = "permission"

    # 权限编码，如 manage:user:create
    code: Mapped[str] = mapped_column(
        "code",
        String(100),
        nullable=False,
        unique=True,
        comment="权限编码",
    )

    # 权限名称
    name: Mapped[str] = mapped_column(
        "name",
        String(100),
        nullable=False,
        comment="权限名称",
    )

    # 类型：menu / button
    type: Mapped[str] = mapped_column(
        "type",
        String(10),
        nullable=False,
        comment="类型：menu/button",
    )

    # menu 类型对应前端路由 name
    route_key: Mapped[str | None] = mapped_column(
        "route_key",
        String(100),
        nullable=True,
        comment="menu 类型对应前端路由 name",
    )

    # 状态：1 启用 0 禁用
    status: Mapped[int] = mapped_column(
        "status",
        SmallInteger,
        nullable=False,
        insert_default=1,
        comment="状态：1 启用 0 禁用",
    )

    created_at: Mapped[datetime] = mapped_column(
        "created_at",
        DateTime,
        nullable=False,
        insert_default=datetime.utcnow,
        comment="创建时间",
    )
    updated_at: Mapped[datetime] = mapped_column(
        "updated_at",
        DateTime,
        nullable=False,
        insert_default=datetime.utcnow,
        onupdate=datetime.utcnow,
        comment="更新时间",
    )


class RolePermission(DBModel, kw_only=True):
    """角色-权限关联（复合主键 role_id + permission_id）"""
    __tablename__ = "role_permission"

    # 角色 ID
    role_id: Mapped[str] = mapped_column(
        "role_id",
        String(36),
        ForeignKey("role.id", ondelete="CASCADE"),
        primary_key=True,
        comment="角色 ID",
    )

    # 权限 ID
    permission_id: Mapped[str] = mapped_column(
        "permission_id",
        String(36),
        ForeignKey("permission.id", ondelete="CASCADE"),
        primary_key=True,
        comment="权限 ID",
    )


class UserRole(DBModel, kw_only=True):
    """用户-角色关联（复合主键 user_id + role_id）"""
    __tablename__ = "user_role"

    # 用户 ID
    user_id: Mapped[str] = mapped_column(
        "user_id",
        String(36),
        ForeignKey("user.id", ondelete="CASCADE"),
        primary_key=True,
        comment="用户 ID",
    )

    # 角色 ID
    role_id: Mapped[str] = mapped_column(
        "role_id",
        String(36),
        ForeignKey("role.id", ondelete="CASCADE"),
        primary_key=True,
        comment="角色 ID",
    )


class RoleDept(DBModel, kw_only=True):
    """角色-部门关联（CUSTOM 数据范围用，复合主键 role_id + dept_id）"""
    __tablename__ = "role_dept"

    # 角色 ID
    role_id: Mapped[str] = mapped_column(
        "role_id",
        String(36),
        ForeignKey("role.id", ondelete="CASCADE"),
        primary_key=True,
        comment="角色 ID",
    )

    # 部门 ID
    dept_id: Mapped[str] = mapped_column(
        "dept_id",
        String(36),
        ForeignKey("department.id", ondelete="CASCADE"),
        primary_key=True,
        comment="部门 ID",
    )


class RefreshToken(DBModel, UUIDMixin, kw_only=True):
    """刷新令牌（只存 SHA-256 哈希）"""
    __tablename__ = "refresh_token"

    # 索引：user_id 普通索引；token_hash 唯一索引（命名走 convention）
    __table_args__ = (
        Index(None, "user_id"),
        Index(None, "token_hash", unique=True),
    )

    # 用户 ID（外键，级联删除）
    user_id: Mapped[str] = mapped_column(
        "user_id",
        String(36),
        ForeignKey("user.id", ondelete="CASCADE"),
        nullable=False,
        comment="用户 ID",
    )

    # Token SHA-256 哈希（不存原文）
    token_hash: Mapped[str] = mapped_column(
        "token_hash",
        String(64),
        nullable=False,
        comment="Token SHA-256 哈希",
    )

    # 过期时间
    expires_at: Mapped[datetime] = mapped_column(
        "expires_at",
        DateTime,
        nullable=False,
        comment="过期时间",
    )

    # 吊销时间，NULL 表示有效
    revoked_at: Mapped[datetime | None] = mapped_column(
        "revoked_at",
        DateTime,
        nullable=True,
        comment="吊销时间",
    )

    # 客户端 User-Agent
    user_agent: Mapped[str | None] = mapped_column(
        "user_agent",
        String(255),
        nullable=True,
        comment="客户端 User-Agent",
    )

    # 客户端 IP
    ip: Mapped[str | None] = mapped_column(
        "ip",
        String(45),
        nullable=True,
        comment="客户端 IP",
    )

    created_at: Mapped[datetime] = mapped_column(
        "created_at",
        DateTime,
        nullable=False,
        insert_default=datetime.utcnow,
        comment="创建时间",
    )
    last_used_at: Mapped[datetime | None] = mapped_column(
        "last_used_at",
        DateTime,
        nullable=True,
        comment="最后使用时间",
    )
