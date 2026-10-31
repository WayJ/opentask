"""
Analysis Request Model

DataInsight智能体分析请求数据模型
"""

from sqlalchemy import Column, String, Text, DateTime, JSON, Integer, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
from typing import List, Dict, Any, Optional

from opentask.models.base import DBModel, UUIDMixin


class AnalysisRequest(DBModel, UUIDMixin, kw_only=True):
    """分析请求模型"""

    __tablename__ = "analysis_requests"

    # 关联信息
    session_id: str = Column(
        UUID(as_uuid=True),
        ForeignKey("datainsight_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    connection_id: Optional[str] = Column(
        UUID(as_uuid=True),
        ForeignKey("connections.id"),
        nullable=True,
        index=True
    )

    # 请求内容
    user_input: str = Column(Text, nullable=False)
    files: List[str] = Column(
        JSON,
        nullable=False,
        default=list
    )
    context: Dict[str, Any] = Column(
        JSON,
        nullable=False,
        default=dict
    )

    # 状态管理
    status: str = Column(
        String(50),
        nullable=False,
        default="pending",
        index=True
    )  # pending, analyzing, executing, completed, failed, cancelled

    # AI分析结果
    intent_analysis: Optional[Dict[str, Any]] = Column(
        JSON,
        nullable=True
    )
    selected_tools: List[Dict[str, Any]] = Column(
        JSON,
        nullable=False,
        default=list
    )
    execution_plan: Optional[Dict[str, Any]] = Column(
        JSON,
        nullable=True
    )

    # 性能指标
    processing_time_ms: Optional[int] = Column(
        Integer,
        nullable=True
    )
    total_executions: int = Column(
        Integer,
        nullable=False,
        default=0
    )
    successful_executions: int = Column(
        Integer,
        nullable=False,
        default=0
    )

    # 时间戳
    created_at: datetime = Column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
        index=True
    )
    started_at: Optional[datetime] = Column(
        DateTime(timezone=True),
        nullable=True
    )
    completed_at: Optional[datetime] = Column(
        DateTime(timezone=True),
        nullable=True
    )

    # 关系
    session = relationship(
        "DataInsightSession",
        back_populates="requests"
    )
    executions = relationship(
        "AnalysisExecution",
        back_populates="request",
        cascade="all, delete-orphan"
    )
    results = relationship(
        "AnalysisResult",
        back_populates="request",
        cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<AnalysisRequest(id={self.id}, status={self.status}, user_input={self.user_input[:50]}...)>"

    def to_dict(self) -> dict:
        """转换为字典格式"""
        return {
            "id": str(self.id),
            "session_id": str(self.session_id),
            "connection_id": str(self.connection_id) if self.connection_id else None,
            "user_input": self.user_input,
            "files": self.files,
            "context": self.context,
            "status": self.status,
            "intent_analysis": self.intent_analysis,
            "selected_tools": self.selected_tools,
            "execution_plan": self.execution_plan,
            "processing_time_ms": self.processing_time_ms,
            "total_executions": self.total_executions,
            "successful_executions": self.successful_executions,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }

    def is_pending(self) -> bool:
        """检查请求是否待处理"""
        return self.status == "pending"

    def is_running(self) -> bool:
        """检查请求是否正在执行"""
        return self.status in ["analyzing", "executing"]

    def is_completed(self) -> bool:
        """检查请求是否已完成"""
        return self.status == "completed"

    def is_failed(self) -> bool:
        """检查请求是否失败"""
        return self.status == "failed"

    def start_execution(self) -> None:
        """开始执行请求"""
        self.status = "executing"
        self.started_at = datetime.utcnow()

    def complete_execution(self) -> None:
        """完成执行请求"""
        self.status = "completed"
        self.completed_at = datetime.utcnow()
        if self.started_at:
            self.processing_time_ms = int(
                (self.completed_at - self.started_at).total_seconds() * 1000
            )

    def fail_execution(self, error_message: str = None) -> None:
        """执行失败"""
        self.status = "failed"
        self.completed_at = datetime.utcnow()
        if self.started_at:
            self.processing_time_ms = int(
                (self.completed_at - self.started_at).total_seconds() * 1000
            )

    def cancel_execution(self) -> None:
        """取消执行"""
        self.status = "cancelled"
        self.completed_at = datetime.utcnow()

    def get_success_rate(self) -> float:
        """获取成功率"""
        if self.total_executions == 0:
            return 0.0
        return self.successful_executions / self.total_executions

    def update_execution_stats(self, successful: bool = True) -> None:
        """更新执行统计"""
        self.total_executions += 1
        if successful:
            self.successful_executions += 1