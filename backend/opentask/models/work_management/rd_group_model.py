"""研发组数据模型"""
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, List, Optional
from sqlalchemy import String, DateTime, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.mysql import ENUM

from opentask.models.base import DBModel
from .enums import RdGroupStatus, RdGroupRole


if TYPE_CHECKING:
    from opentask.models.user.model import UserModel


def generate_uuid() -> str:
    """生成 UUID（36字符，带连字符）"""
    return str(uuid.uuid4())


class RdGroup(DBModel):
    """研发组模型"""
    __tablename__ = "rd_groups"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, insert_default=generate_uuid)
    name: Mapped[str] = mapped_column(String(100), nullable=False, comment="研发组名称")
    director_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("user.id"),
        nullable=False,
        comment="产品总监"
    )
    leader_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("user.id"),
        nullable=False,
        comment="组长"
    )
    status: Mapped[str] = mapped_column(
        ENUM(RdGroupStatus, name="rd_group_status"),
        nullable=False,
        insert_default=RdGroupStatus.ACTIVE,
        comment="状态"
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, insert_default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, insert_default=datetime.utcnow, onupdate=datetime.utcnow)

    # 关系暂时注释掉，避免greenlet错误
    # members: Mapped[List["RdGroupMember"]] = relationship(
    #     "RdGroupMember",
    #     back_populates="group",
    #     cascade="all, delete-orphan"
    # )


class RdGroupMember(DBModel):
    """研发组成员模型"""
    __tablename__ = "rd_group_members"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, insert_default=generate_uuid)
    group_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("rd_groups.id"),
        nullable=False,
        comment="所属组"
    )
    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("user.id"),
        nullable=False,
        comment="用户"
    )
    role: Mapped[str] = mapped_column(
        ENUM(RdGroupRole, name="rd_group_role"),
        nullable=False,
        comment="组内角色"
    )
    joined_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, insert_default=datetime.utcnow, comment="加入时间")

    # 关系暂时注释掉
    # group: Mapped["RdGroup"] = relationship("RdGroup", back_populates="members")

    __table_args__ = (
        Index("ix_rd_group_members_group_user", "group_id", "user_id", unique=True),
    )
