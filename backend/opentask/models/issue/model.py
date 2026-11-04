"""Issue 数据模型"""
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, List, Optional
from sqlalchemy import String, Integer, Text, Boolean, ForeignKey, DateTime, Numeric, JSON, Index, and_
from sqlalchemy.orm import Mapped, mapped_column, relationship, foreign
from sqlalchemy import Enum as ENUM

from opentask.models.base import DBModel
from .enums import IssueType, IssueStatus, IssuePriority, CommentType, RelationType, TimelineAction


if TYPE_CHECKING:
    from opentask.models.user.model import UserModel


def generate_uuid() -> str:
    """生成 UUID"""
    return str(uuid.uuid4())


class Issue(DBModel):
    """Issue 主模型"""
    __tablename__ = "issues"

    # 主键
    id: Mapped[str] = mapped_column(String(36), primary_key=True, insert_default=generate_uuid)

    # 问题编号（格式：ISSUE2026-1）
    issue_code: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        unique=True,
        index=True,
        comment="问题编号"
    )

    # 基本信息
    title: Mapped[str] = mapped_column(String(255), nullable=False, comment="标题")
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="描述")

    # 类型、状态、优先级 - 直接使用枚举值字符串而不是 Enum 类
    type: Mapped[str] = mapped_column(
        ENUM("bug", "feature", "question", "feedback", "incident", "improvement", name="issue_type"),
        nullable=False,
        comment="类型"
    )
    status: Mapped[str] = mapped_column(
        ENUM("open", "in_progress", "feedback", "resolved", "closed", "rejected", name="issue_status"),
        nullable=False,
        insert_default="open",
        comment="状态"
    )
    priority: Mapped[str] = mapped_column(
        ENUM("low", "medium", "high", "critical", name="issue_priority"),
        nullable=False,
        insert_default="medium",
        comment="优先级"
    )

    # 关联实体
    project_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        nullable=True,
        index=True,
        comment="项目 ID"
    )
    workspace_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("workspaces.id"),
        nullable=True,
        index=True,
        comment="所属工作区"
    )
    task_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        nullable=True,
        index=True,
        comment="任务 ID"
    )
    requirement_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        nullable=True,
        index=True,
        comment="需求 ID"
    )

    # 一等公民父子（E4-S3）；不用 IssueRelation 表达父子
    parent_issue_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("issues.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="父 Issue ID"
    )

    # 分配信息
    assignee_id: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        index=True,
        comment="负责人 ID"
    )
    reporter_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
        comment="报告人 ID"
    )

    # 统计信息
    view_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        insert_default=0,
        comment="浏览次数"
    )
    comment_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        insert_default=0,
        comment="评论数量"
    )
    attachment_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        insert_default=0,
        comment="附件数量"
    )

    # 排序
    position: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="排序位置"
    )

    # 时间跟踪
    due_date: Mapped[Optional[datetime]] = mapped_column(
        DateTime,
        nullable=True,
        index=True,
        comment="截止日期"
    )
    started_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime,
        nullable=True,
        comment="开始时间"
    )
    resolved_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime,
        nullable=True,
        comment="解决时间"
    )
    closed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime,
        nullable=True,
        comment="关闭时间"
    )

    # 工时估算
    estimated_hours: Mapped[Optional[float]] = mapped_column(
        Numeric(5, 2),
        nullable=True,
        comment="预估工时"
    )
    actual_hours: Mapped[Optional[float]] = mapped_column(
        Numeric(5, 2),
        nullable=True,
        comment="实际工时"
    )

    # Cycle 归属（E6-S2）
    cycle_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("cycles.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="所属 Cycle ID",
    )
    estimate_points: Mapped[Optional[float]] = mapped_column(
        Numeric(8, 2),
        nullable=True,
        comment="故事点估算（可选）",
    )

    # 软删除
    is_deleted: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        insert_default=False,
        comment="是否已删除"
    )

    # 审计字段
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        insert_default=datetime.utcnow,
        comment="创建时间"
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        insert_default=datetime.utcnow,
        onupdate=datetime.utcnow,
        comment="更新时间"
    )
    created_by: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment="创建人"
    )
    updated_by: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment="更新人"
    )

    # 部门归属快照
    dept_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("department.id"),
        nullable=True,
        index=True,
        comment="部门归属快照（创建时所属部门）"
    )

    # 关系
    comments: Mapped[List["IssueComment"]] = relationship(
        "IssueComment",
        back_populates="issue",
        cascade="all, delete-orphan"
    )
    relations_as_source: Mapped[List["IssueRelation"]] = relationship(
        "IssueRelation",
        foreign_keys="IssueRelation.source_id",
        back_populates="source_issue",
        cascade="all, delete-orphan"
    )
    relations_as_target: Mapped[List["IssueRelation"]] = relationship(
        "IssueRelation",
        foreign_keys="IssueRelation.target_id",
        back_populates="target_issue",
        cascade="all, delete-orphan"
    )
    timeline: Mapped[List["IssueTimeline"]] = relationship(
        "IssueTimeline",
        back_populates="issue",
        cascade="all, delete-orphan"
    )
    tags: Mapped[List["IssueTag"]] = relationship(
        "IssueTag",
        back_populates="issue",
        cascade="all, delete-orphan"
    )
    reactions: Mapped[List["IssueReaction"]] = relationship(
        "IssueReaction",
        back_populates="issue",
        cascade="all, delete-orphan",
        order_by="IssueReaction.created_at.desc()"
    )

    # 用户关系
    assignee: Mapped[Optional["UserModel"]] = relationship(
        "UserModel",
        primaryjoin="Issue.assignee_id == foreign(UserModel.id)",
        foreign_keys="Issue.assignee_id",
        lazy="joined",
        uselist=False
    )
    reporter: Mapped[Optional["UserModel"]] = relationship(
        "UserModel",
        primaryjoin="Issue.reporter_id == foreign(UserModel.id)",
        foreign_keys="Issue.reporter_id",
        overlaps="assignee",
        lazy="joined",
        uselist=False
    )

    parent: Mapped[Optional["Issue"]] = relationship(
        "Issue",
        remote_side="Issue.id",
        foreign_keys="Issue.parent_issue_id",
    )

    # 索引
    __table_args__ = (
        Index("idx_issues_issue_code", "issue_code", unique=True),
        Index("idx_issues_type", "type"),
        Index("idx_issues_status", "status"),
        Index("idx_issues_priority", "priority"),
        Index("idx_issues_project", "project_id"),
        Index("idx_issues_workspace", "workspace_id"),
        Index("idx_issues_assignee", "assignee_id"),
        Index("idx_issues_reporter", "reporter_id"),
        Index("idx_issues_created_at", "created_at"),
        Index("idx_issues_updated_at", "updated_at"),
        Index("idx_issues_due_date", "due_date"),
        Index("idx_issues_project_status", "project_id", "status"),
        Index("idx_issues_assignee_status", "assignee_id", "status"),
        Index("idx_issues_parent", "parent_issue_id"),
        Index("idx_issues_cycle", "cycle_id"),
    )


class IssueComment(DBModel):
    """Issue 评论模型"""
    __tablename__ = "issue_comments"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, insert_default=generate_uuid)

    issue_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("issues.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Issue ID"
    )

    user_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
        comment="用户 ID"
    )

    content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="评论内容"
    )

    # 支持嵌套评论
    parent_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("issue_comments.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
        comment="父评论 ID"
    )

    comment_type: Mapped[CommentType] = mapped_column(
        ENUM(CommentType, name="comment_type"),
        nullable=False,
        insert_default=CommentType.COMMENT,
        comment="评论类型"
    )

    meta_data: Mapped[Optional[dict]] = mapped_column(
        "metadata",
        JSON,
        nullable=True,
        comment="元数据"
    )

    is_deleted: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        insert_default=False,
        comment="是否已删除"
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        insert_default=datetime.utcnow,
        comment="创建时间"
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        insert_default=datetime.utcnow,
        onupdate=datetime.utcnow,
        comment="更新时间"
    )

    # 关系
    issue: Mapped["Issue"] = relationship("Issue", back_populates="comments")
    parent: Mapped[Optional["IssueComment"]] = relationship(
        "IssueComment",
        remote_side="IssueComment.id",
        back_populates="replies"
    )
    replies: Mapped[List["IssueComment"]] = relationship(
        "IssueComment",
        back_populates="parent",
        cascade="all, delete-orphan"
    )

    # 索引
    __table_args__ = (
        Index("idx_issue_comments_issue", "issue_id"),
        Index("idx_issue_comments_parent", "parent_id"),
        Index("idx_issue_comments_user", "user_id"),
    )


class IssueRelation(DBModel):
    """Issue 关系模型"""
    __tablename__ = "issue_relations"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True
    )

    source_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("issues.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="源 Issue ID"
    )

    target_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("issues.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="目标 Issue ID"
    )

    relation_type: Mapped[str] = mapped_column(
        ENUM("blocks", "is_blocked_by", "relates_to", "duplicates",
             "is_duplicated_by", "depends_on", "is_depended_by",
             name="relation_type"),
        nullable=False,
        index=True,
        comment="关系类型"
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        insert_default=datetime.utcnow,
        comment="创建时间"
    )
    created_by: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment="创建人"
    )

    # 关系
    source_issue: Mapped["Issue"] = relationship(
        "Issue",
        foreign_keys=[source_id],
        back_populates="relations_as_source"
    )
    target_issue: Mapped["Issue"] = relationship(
        "Issue",
        foreign_keys=[target_id],
        back_populates="relations_as_target"
    )

    # 索引
    __table_args__ = (
        Index("idx_issue_relations_source", "source_id"),
        Index("idx_issue_relations_target", "target_id"),
        Index("idx_issue_relations_type", "relation_type"),
    )


class IssueTimeline(DBModel):
    """Issue 时间线模型"""
    __tablename__ = "issue_timeline"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, insert_default=generate_uuid)

    issue_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("issues.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Issue ID"
    )

    user_id: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        index=True,
        comment="用户 ID"
    )

    action_type: Mapped[str] = mapped_column(
        ENUM("created", "updated", "commented", "status_changed", "assigned",
             "priority_changed", "due_date_changed", "relation_added",
             "relation_removed", "attachment_added", "attachment_removed",
             "label_added", "label_removed", "reaction_added", "reaction_removed",
             "resolved", "closed", "reopened",
             name="timeline_action"),
        nullable=False,
        index=True,
        comment="动作类型"
    )

    action_data: Mapped[Optional[dict]] = mapped_column(
        JSON,
        nullable=True,
        comment="动作数据"
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        insert_default=datetime.utcnow,
        comment="创建时间"
    )

    # 关系
    issue: Mapped["Issue"] = relationship("Issue", back_populates="timeline")

    # 索引
    __table_args__ = (
        Index("idx_issue_timeline_issue", "issue_id"),
        Index("idx_issue_timeline_user", "user_id"),
        Index("idx_issue_timeline_type", "action_type"),
    )


class IssueTag(DBModel):
    """Issue-标签关联模型"""
    __tablename__ = "issue_tags"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True
    )

    issue_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("issues.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Issue ID"
    )

    tag_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("tags.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="标签 ID"
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        insert_default=datetime.utcnow,
        comment="创建时间"
    )

    # 关系
    issue: Mapped["Issue"] = relationship("Issue", back_populates="tags")
    tag: Mapped["Tag"] = relationship("Tag")  # noqa: F821 — Tag in models.tag

    # 索引
    __table_args__ = (
        Index("idx_issue_tags_issue", "issue_id"),
        Index("idx_issue_tags_tag", "tag_id"),
    )


class IssueReaction(DBModel):
    """Issue 反应表"""
    __tablename__ = "issue_reactions"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True
    )

    issue_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("issues.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Issue ID"
    )

    emoji: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
        index=True,
        comment="表情符号"
    )

    user_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
        comment="用户 ID"
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        insert_default=datetime.utcnow,
        comment="创建时间"
    )

    # 关系
    issue: Mapped["Issue"] = relationship("Issue", back_populates="reactions")

    # 索引和约束
    __table_args__ = (
        Index("idx_issue_reactions_issue", "issue_id"),
        Index("idx_issue_reactions_emoji", "emoji"),
        Index("idx_issue_reactions_user", "user_id"),
        Index("idx_issue_reactions_issue_emoji", "issue_id", "emoji"),
        Index("uq_issue_reaction", "issue_id", "emoji", "user_id", unique=True),
    )
