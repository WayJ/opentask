"""
DataInsight Session Model

DataInsight智能体会话数据模型
"""

from sqlalchemy import Column, String, Text, DateTime, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime

from opentask.models.base import DBModel, UUIDMixin


class DataInsightSession(DBModel, UUIDMixin, kw_only=True):
    """DataInsight智能体会话模型"""

    __tablename__ = "datainsight_sessions"

    # 基本信息
    user_id: str = Column(UUID(as_uuid=True), nullable=False, index=True)
    title: str = Column(String(255), nullable=False)
    description: str = Column(Text, nullable=True)

    # 状态管理
    status: str = Column(
        String(50),
        nullable=False,
        default="active",
        index=True
    )  # active, completed, archived

    # 会话上下文
    context: dict = Column(
        JSON,
        nullable=False,
        default=dict
    )  # 用户偏好、历史记录等

    # 时间戳
    created_at: datetime = Column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
        index=True
    )
    updated_at: datetime = Column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )
    ended_at: datetime = Column(
        DateTime(timezone=True),
        nullable=True
    )

    # 关系
    requests = relationship(
        "AnalysisRequest",
        back_populates="session",
        cascade="all, delete-orphan"
    )
    reports = relationship(
        "AnalysisReport",
        back_populates="session",
        cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<DataInsightSession(id={self.id}, title={self.title}, status={self.status})>"

    def to_dict(self) -> dict:
        """转换为字典格式"""
        return {
            "id": str(self.id),
            "user_id": str(self.user_id),
            "title": self.title,
            "description": self.description,
            "status": self.status,
            "context": self.context,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "ended_at": self.ended_at.isoformat() if self.ended_at else None,
        }

    def is_active(self) -> bool:
        """检查会话是否活跃"""
        return self.status == "active"

    def mark_completed(self) -> None:
        """标记会话为完成状态"""
        self.status = "completed"
        self.ended_at = datetime.utcnow()

    def archive(self) -> None:
        """归档会话"""
        self.status = "archived"
        if not self.ended_at:
            self.ended_at = datetime.utcnow()

    def update_context(self, new_context: dict) -> None:
        """更新会话上下文"""
        if self.context:
            self.context.update(new_context)
        else:
            self.context = new_context
        self.updated_at = datetime.utcnow()