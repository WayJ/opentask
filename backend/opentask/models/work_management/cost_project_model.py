"""成本承担项目数据模型"""
import uuid
from datetime import datetime
from typing import TYPE_CHECKING
from sqlalchemy import String, Text, DateTime, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.mysql import ENUM

from opentask.models.base import DBModel
from .enums import CostProjectStatus


def generate_uuid() -> str:
    """生成 UUID（36字符，带连字符）"""
    return str(uuid.uuid4())


class CostProject(DBModel):
    """成本承担项目模型"""
    __tablename__ = "cost_projects"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, insert_default=generate_uuid)
    name: Mapped[str] = mapped_column(String(200), nullable=False, comment="项目名称")
    code: Mapped[str] = mapped_column(String(50), nullable=False, unique=True, comment="项目编号")
    description: Mapped[str] = mapped_column(Text, nullable=True, comment="项目描述")
    manager_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("user.id"),
        nullable=False,
        comment="项目经理"
    )
    status: Mapped[str] = mapped_column(
        ENUM(CostProjectStatus, name="cost_project_status"),
        nullable=False,
        insert_default=CostProjectStatus.ACTIVE,
        comment="状态"
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, insert_default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, insert_default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index("ix_cost_projects_code", "code"),
    )
