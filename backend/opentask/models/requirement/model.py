"""需求模块 SQLAlchemy 模型"""
import json
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import JSON, Column, DateTime, String, Text, Integer, Boolean, ForeignKey, Enum as SQLEnum, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from opentask.models.base import DBModel as Base
from opentask.models.requirement.enums import (
    RequirementStatus,
    Priority,
    MergeStatus,
    JobStatus,
    JobType,
)

if TYPE_CHECKING:
    from opentask.models.user.model import User


def generate_uuid() -> str:
    """生成 UUID"""
    return str(uuid.uuid4())


class Requirement(Base):
    """需求模型"""
    __tablename__ = "requirements"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, insert_default=generate_uuid)
    code: Mapped[str] = mapped_column(String(50), nullable=False, unique=True, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[RequirementStatus] = mapped_column(
        String(50), insert_default=RequirementStatus.PLANNING.value, nullable=False
    )
    priority: Mapped[Priority | None] = mapped_column(String(50), nullable=True)
    tags: Mapped[list[str]] = mapped_column(JSON, nullable=False)

    # 元数据
    created_at: Mapped[datetime] = mapped_column(DateTime, insert_default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, insert_default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    created_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    assignee_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    project_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=True, index=True)

    # 部门归属快照
    dept_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("department.id"), nullable=True, index=True,
        comment="部门归属快照（创建时所属部门）"
    )

    # 关联
    project = relationship("Project", back_populates="requirements")
    events = relationship("Event", back_populates="requirement", cascade="all, delete-orphan")
    repos = relationship("RequirementRepo", back_populates="requirement", cascade="all, delete-orphan")
    comments = relationship("Comment", back_populates="requirement", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_requirements_status", "status"),
        Index("idx_requirements_priority", "priority"),
        Index("idx_requirements_created_at", "created_at"),
        Index("idx_requirements_code", "code"),
        Index("idx_requirements_project_id", "project_id"),
    )


class Event(Base):
    """事件模型 - 事件溯源"""
    __tablename__ = "events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, insert_default=generate_uuid)
    requirement_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("requirements.id", ondelete="CASCADE"), nullable=False, index=True
    )
    type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    data: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    actor: Mapped[str | None] = mapped_column(String(255), nullable=True)
    reasoning: Mapped[str | None] = mapped_column(Text, nullable=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, insert_default=datetime.utcnow, nullable=False, index=True)
    snapshot: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)

    # 关联
    requirement = relationship("Requirement", back_populates="events")

    __table_args__ = (
        Index("idx_events_requirement_id", "requirement_id"),
        Index("idx_events_timestamp", "timestamp"),
        Index("idx_events_type", "type"),
    )


class Project(Base):
    """项目模型"""
    __tablename__ = "projects"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, insert_default=generate_uuid)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, insert_default=True, nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime, insert_default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, insert_default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # 部门归属快照
    dept_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("department.id"), nullable=True, index=True,
        comment="部门归属快照（创建时所属部门）"
    )

    # 工作区租户（E3-S1；存量回填后非空，模型层暂可空以兼容测试 create_all）
    workspace_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("workspaces.id"), nullable=True, index=True,
        comment="所属工作区",
    )

    # 项目时间盒（E8-S1 Timeline）
    starts_at: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True, comment="项目开始时间"
    )
    target_date: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True, comment="项目目标日期"
    )

    # 健康缓存（E8-S2）
    health_status: Mapped[str | None] = mapped_column(
        String(20), nullable=True, comment="on_track|at_risk|off_track"
    )
    health_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    health_updated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    health_updated_by: Mapped[str | None] = mapped_column(String(36), nullable=True)

    # 关联
    requirements = relationship("Requirement", back_populates="project", cascade="all, delete-orphan")
    repos = relationship("RepoConfig", back_populates="project", cascade="all, delete-orphan")
    knowledge_bases = relationship(
        "KnowledgeBase",
        secondary="project_knowledge_bases",
        back_populates="projects",
    )

    __table_args__ = (
        Index("idx_projects_is_active", "is_active"),
        Index("idx_projects_workspace", "workspace_id"),
        Index("uq_projects_workspace_name", "workspace_id", "name", unique=True),
    )


class RepoConfig(Base):
    """仓库配置模型"""
    __tablename__ = "repo_configs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    project_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    url: Mapped[str] = mapped_column(String(500), nullable=False)
    main_branch: Mapped[str] = mapped_column(String(100), insert_default="main", nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime, insert_default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, insert_default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # 关联
    project = relationship("Project", back_populates="repos")
    requirements = relationship("RequirementRepo", back_populates="repo", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_repo_configs_project_name", "project_id", "name", unique=True),
    )


class RequirementRepo(Base):
    """需求-仓库关联模型"""
    __tablename__ = "requirement_repos"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, insert_default=generate_uuid)
    requirement_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("requirements.id", ondelete="CASCADE"), nullable=False, index=True
    )
    repo_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("repo_configs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    branch: Mapped[str | None] = mapped_column(String(255), nullable=True)
    pr_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    merge_status: Mapped[MergeStatus | None] = mapped_column(SQLEnum(MergeStatus), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, insert_default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, insert_default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # 关联
    requirement = relationship("Requirement", back_populates="repos")
    repo = relationship("RepoConfig", back_populates="requirements")

    __table_args__ = (
        Index("idx_requirement_repos_requirement_repo", "requirement_id", "repo_id", unique=True),
        Index("idx_requirement_repos_repo_id", "repo_id"),
    )


class Comment(Base):
    """评论模型"""
    __tablename__ = "requirement_comments"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, insert_default=generate_uuid)
    requirement_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("requirements.id", ondelete="CASCADE"), nullable=False, index=True
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    user_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_deleted: Mapped[bool] = mapped_column(Boolean, insert_default=False, nullable=False)
    embedded_tasks: Mapped[list | None] = mapped_column(JSON, nullable=True, comment="嵌入式任务列表")

    created_at: Mapped[datetime] = mapped_column(DateTime, insert_default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, insert_default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # 关联
    requirement = relationship("Requirement", back_populates="comments")

    __table_args__ = (
        Index("idx_requirement_comments_requirement_id", "requirement_id"),
        Index("idx_requirement_comments_created_at", "created_at"),
        Index("idx_requirement_comments_is_deleted", "is_deleted"),
    )


class QueueJob(Base):
    """队列任务记录模型"""
    __tablename__ = "queue_jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, insert_default=generate_uuid)
    requirement_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    type: Mapped[JobType] = mapped_column(SQLEnum(JobType), nullable=False, index=True)
    status: Mapped[JobStatus] = mapped_column(
        SQLEnum(JobStatus), insert_default=JobStatus.PENDING, nullable=False, index=True
    )
    data: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    result: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)

    # 重试相关
    attempts: Mapped[int] = mapped_column(Integer, insert_default=0, nullable=False)
    max_attempts: Mapped[int] = mapped_column(Integer, insert_default=3, nullable=False)

    # 时间戳
    created_at: Mapped[datetime] = mapped_column(DateTime, insert_default=datetime.utcnow, nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    __table_args__ = (
        Index("idx_queue_jobs_requirement_id", "requirement_id"),
        Index("idx_queue_jobs_status", "status"),
        Index("idx_queue_jobs_type", "type"),
    )


class RequirementCodeSequence(Base):
    """需求编码序列表"""
    __tablename__ = "requirement_code_sequence"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    year: Mapped[int] = mapped_column(Integer, nullable=False, unique=True, index=True)
    sequence: Mapped[int] = mapped_column(Integer, nullable=False, insert_default=0)

    __table_args__ = (
        Index("idx_requirements_code_sequence_year", "year"),
    )
