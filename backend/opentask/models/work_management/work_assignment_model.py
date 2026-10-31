"""工作安排数据模型"""
import uuid
from datetime import datetime, date
from typing import TYPE_CHECKING, List, Optional
from sqlalchemy import String, Text, Date, Numeric, DateTime, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import Enum as ENUM

from opentask.models.base import DBModel
from .enums import WorkStatus, QualityLevel, RelatedType


def generate_uuid() -> str:
    """生成 UUID（36字符，带连字符）"""
    return str(uuid.uuid4())


class WorkAssignment(DBModel):
    """工作安排模型"""
    __tablename__ = "work_assignments"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, insert_default=generate_uuid)
    title: Mapped[str] = mapped_column(String(200), nullable=False, comment="工作内容")
    assignee_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("user.id"),
        nullable=False,
        comment="被分配人"
    )
    assigner_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("user.id"),
        nullable=False,
        comment="分配人"
    )
    group_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("rd_groups.id"),
        nullable=False,
        comment="所属研发组"
    )
    cost_project_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("cost_projects.id"),
        nullable=False,
        comment="成本承担项目"
    )
    deadline: Mapped[date] = mapped_column(Date, nullable=False, comment="完成时间要求")
    estimated_hours: Mapped[float] = mapped_column(Numeric(6, 1), nullable=False, comment="工作量（小时）")
    week_start: Mapped[date] = mapped_column(Date, nullable=False, index=True, comment="所属周")
    status: Mapped[str] = mapped_column(
        ENUM(WorkStatus, name="work_status"),
        nullable=False,
        insert_default=WorkStatus.NOT_STARTED,
        comment="工作状态"
    )
    related_type: Mapped[Optional[str]] = mapped_column(
        ENUM(RelatedType, name="related_type"),
        nullable=True,
        comment="关联类型"
    )
    related_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True, comment="关联ID")
    quality: Mapped[str] = mapped_column(
        ENUM(QualityLevel, name="quality_level"),
        nullable=False,
        insert_default=QualityLevel.UNKNOWN,
        comment="质量评估"
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, insert_default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, insert_default=datetime.utcnow, onupdate=datetime.utcnow)

    # 关系
    feedbacks: Mapped[List["WorkFeedback"]] = relationship(
        "WorkFeedback",
        back_populates="assignment",
        cascade="all, delete-orphan"
    )
    attachments: Mapped[List["WorkAssignmentAttachment"]] = relationship(
        "WorkAssignmentAttachment",
        back_populates="assignment",
        cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_work_assignments_assignee", "assignee_id"),
        Index("ix_work_assignments_week", "week_start"),
        Index("ix_work_assignments_deadline_status", "deadline", "status"),
    )
