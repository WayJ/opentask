"""工作反馈数据模型"""
import uuid
from datetime import datetime, date
from typing import TYPE_CHECKING, Optional
from sqlalchemy import String, Text, Date, Boolean, DateTime, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.mysql import ENUM

from opentask.models.base import DBModel
from .enums import WorkStatus, UnplannedType


def generate_uuid() -> str:
    """生成 UUID（36字符，带连字符）"""
    return str(uuid.uuid4())


class WorkFeedback(DBModel):
    """工作反馈模型"""
    __tablename__ = "work_feedback"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, insert_default=generate_uuid)
    assignment_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("work_assignments.id"),
        nullable=True,
        comment="关联工作安排"
    )
    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("user.id"),
        nullable=False,
        comment="反馈人"
    )
    feedback_date: Mapped[date] = mapped_column(Date, nullable=False, comment="反馈日期")
    content: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="反馈内容")
    status: Mapped[str] = mapped_column(
        ENUM(WorkStatus, name="work_status"),
        nullable=False,
        comment="工作状态"
    )
    is_planned: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, comment="是否计划内")
    unplanned_type: Mapped[Optional[str]] = mapped_column(
        ENUM(UnplannedType, name="unplanned_type"),
        nullable=True,
        comment="计划外类型"
    )
    unplanned_related_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True, comment="计划外关联ID")
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, insert_default=datetime.utcnow)

    # 关系
    assignment: Mapped[Optional["WorkAssignment"]] = relationship("WorkAssignment", back_populates="feedbacks")

    __table_args__ = (
        Index("ix_work_feedback_user_date", "user_id", "feedback_date"),
    )
