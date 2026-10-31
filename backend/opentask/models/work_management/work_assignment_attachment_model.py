"""工作安排附件数据模型"""
import uuid
from datetime import datetime
from sqlalchemy import String, BigInteger, DateTime, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from opentask.models.base import DBModel


def generate_uuid() -> str:
    """生成 UUID（36字符，带连字符）"""
    return str(uuid.uuid4())


class WorkAssignmentAttachment(DBModel):
    """工作安排附件模型"""
    __tablename__ = "work_assignment_attachments"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, insert_default=generate_uuid)
    assignment_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("work_assignments.id"),
        nullable=False,
        comment="关联工作安排"
    )
    file_name: Mapped[str] = mapped_column(String(255), nullable=False, comment="文件名")
    file_path: Mapped[str] = mapped_column(String(500), nullable=False, comment="存储路径")
    file_size: Mapped[int] = mapped_column(BigInteger, nullable=False, comment="文件大小")
    uploaded_by: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("user.id"),
        nullable=False,
        comment="上传人"
    )
    uploaded_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, insert_default=datetime.utcnow, comment="上传时间")

    # 关系
    assignment: Mapped["WorkAssignment"] = relationship("WorkAssignment", back_populates="attachments")

    __table_args__ = (
        Index("ix_work_attachments_assignment", "assignment_id"),
    )
