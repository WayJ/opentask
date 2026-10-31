"""Repository SQLAlchemy 模型"""
import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import String, Integer, Text, ForeignKey, DateTime, Boolean, JSON, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from opentask.models.base import DBModel
from .enums import RepoStatus, GitProvider

if TYPE_CHECKING:
    from opentask.models.requirement.model import Requirement


def generate_uuid() -> str:
    """生成 UUID"""
    return str(uuid.uuid4())


class Repository(DBModel):
    """仓库模型"""
    __tablename__ = "repositories"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, insert_default=generate_uuid)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    url: Mapped[str] = mapped_column(String(500), nullable=False)
    local_path: Mapped[str | None] = mapped_column(Text, nullable=True)

    # 关联
    project_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    requirement_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("requirements.id", ondelete="CASCADE"),
        nullable=True,
        index=True
    )

    # Git 配置
    branch: Mapped[str] = mapped_column(String(255), insert_default="main", nullable=False)
    provider: Mapped[str] = mapped_column(String(50), insert_default=GitProvider.CUSTOM, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, insert_default=True, nullable=False)
    status: Mapped[str] = mapped_column(String(50), insert_default=RepoStatus.IDLE, nullable=False)

    # 额外配置
    auth_token: Mapped[str | None] = mapped_column(String(500), nullable=True)  # 加密存储

    # 元数据
    last_clone_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_pull_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_commit: Mapped[str | None] = mapped_column(String(100), nullable=True)  # 最后一次提交的 hash
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        insert_default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        insert_default=datetime.utcnow,
        onupdate=datetime.utcnow
    )

    # 关系
    project = relationship("Project", backref="repositories")
    requirement = relationship("Requirement", backref="repositories")
    branches = relationship("RepositoryBranch", back_populates="repository", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Repository(id={self.id}, name={self.name}, url={self.url}, status={self.status})>"

    __table_args__ = (
        Index("idx_repositories_project_id", "project_id"),
        Index("idx_repositories_requirement_id", "requirement_id"),
        Index("idx_repositories_status", "status"),
        Index("idx_repositories_is_active", "is_active"),
    )


class RepositoryBranch(DBModel):
    """仓库分支模型"""
    __tablename__ = "repository_branches"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    repository_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("repositories.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    is_default: Mapped[bool] = mapped_column(Boolean, insert_default=False, nullable=False)
    last_commit: Mapped[str | None] = mapped_column(String(100), nullable=True)
    commit_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    commit_author: Mapped[str | None] = mapped_column(String(255), nullable=True)
    committed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        insert_default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        insert_default=datetime.utcnow,
        onupdate=datetime.utcnow
    )

    # 关系
    repository = relationship("Repository", back_populates="branches")

    def __repr__(self) -> str:
        return f"<RepositoryBranch(id={self.id}, name={self.name}, is_default={self.is_default})>"

    __table_args__ = (
        Index("idx_repository_branches_repository_id", "repository_id"),
        Index("idx_repository_branches_name", "repository_id", "name", unique=True),
    )
