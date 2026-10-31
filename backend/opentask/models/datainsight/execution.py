"""
Analysis Execution Model

DataInsight智能体分析执行记录模型
"""

from sqlalchemy import Column, String, Text, DateTime, JSON, Integer, ForeignKey, Numeric
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
from typing import List, Dict, Any, Optional

from opentask.models.base import DBModel, UUIDMixin


class AnalysisExecution(DBModel, UUIDMixin, kw_only=True):
    """分析执行记录模型"""

    __tablename__ = "analysis_executions"

    # 关联信息
    request_id: str = Column(
        UUID(as_uuid=True),
        ForeignKey("analysis_requests.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # 工具信息
    tool_name: str = Column(String(100), nullable=False, index=True)
    tool_type: str = Column(String(50), nullable=False, index=True)
    parameters: Dict[str, Any] = Column(
        JSON,
        nullable=False,
        default=dict
    )

    # 执行状态
    status: str = Column(
        String(50),
        nullable=False,
        default="pending",
        index=True
    )  # pending, running, completed, failed, cancelled

    # 执行结果
    result_data: Optional[Dict[str, Any]] = Column(
        JSON,
        nullable=True
    )
    error_message: Optional[str] = Column(
        Text,
        nullable=True
    )

    # 性能指标
    execution_time_ms: Optional[int] = Column(
        Integer,
        nullable=True
    )
    confidence_score: Optional[float] = Column(
        Numeric(3, 2),
        nullable=True
    )  # 0.00-1.00

    # 分析产出
    insights: List[str] = Column(
        JSON,
        nullable=False,
        default=list
    )
    visualizations: List[Dict[str, Any]] = Column(
        JSON,
        nullable=False,
        default=list
    )
    metrics: Dict[str, Any] = Column(
        JSON,
        nullable=False,
        default=dict
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
    request = relationship(
        "AnalysisRequest",
        back_populates="executions"
    )
    results = relationship(
        "AnalysisResult",
        back_populates="execution",
        cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<AnalysisExecution(id={self.id}, tool={self.tool_name}, status={self.status})>"

    def to_dict(self) -> dict:
        """转换为字典格式"""
        return {
            "id": str(self.id),
            "request_id": str(self.request_id),
            "tool_name": self.tool_name,
            "tool_type": self.tool_type,
            "parameters": self.parameters,
            "status": self.status,
            "result_data": self.result_data,
            "error_message": self.error_message,
            "execution_time_ms": self.execution_time_ms,
            "confidence_score": float(self.confidence_score) if self.confidence_score else None,
            "insights": self.insights,
            "visualizations": self.visualizations,
            "metrics": self.metrics,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }

    def is_pending(self) -> bool:
        """检查是否待执行"""
        return self.status == "pending"

    def is_running(self) -> bool:
        """检查是否正在执行"""
        return self.status == "running"

    def is_completed(self) -> bool:
        """检查是否已完成"""
        return self.status == "completed"

    def is_failed(self) -> bool:
        """检查是否失败"""
        return self.status == "failed"

    def start_execution(self) -> None:
        """开始执行"""
        self.status = "running"
        self.started_at = datetime.utcnow()

    def complete_execution(self, result_data: Dict[str, Any] = None,
                          insights: List[str] = None,
                          visualizations: List[Dict[str, Any]] = None,
                          metrics: Dict[str, Any] = None,
                          confidence_score: float = None) -> None:
        """完成执行"""
        self.status = "completed"
        self.completed_at = datetime.utcnow()

        if self.started_at:
            self.execution_time_ms = int(
                (self.completed_at - self.started_at).total_seconds() * 1000
            )

        if result_data:
            self.result_data = result_data
        if insights:
            self.insights = insights
        if visualizations:
            self.visualizations = visualizations
        if metrics:
            self.metrics = metrics
        if confidence_score is not None:
            self.confidence_score = confidence_score

    def fail_execution(self, error_message: str) -> None:
        """执行失败"""
        self.status = "failed"
        self.completed_at = datetime.utcnow()
        self.error_message = error_message

        if self.started_at:
            self.execution_time_ms = int(
                (self.completed_at - self.started_at).total_seconds() * 1000
            )

    def cancel_execution(self) -> None:
        """取消执行"""
        self.status = "cancelled"
        self.completed_at = datetime.utcnow()

    def add_insight(self, insight: str) -> None:
        """添加洞察"""
        if self.insights:
            self.insights.append(insight)
        else:
            self.insights = [insight]

    def add_visualization(self, visualization: Dict[str, Any]) -> None:
        """添加可视化配置"""
        if self.visualizations:
            self.visualizations.append(visualization)
        else:
            self.visualizations = [visualization]

    def update_metric(self, key: str, value: Any) -> None:
        """更新指标"""
        if self.metrics:
            self.metrics[key] = value
        else:
            self.metrics = {key: value}

    def get_primary_insight(self) -> Optional[str]:
        """获取主要洞察"""
        if self.insights and len(self.insights) > 0:
            return self.insights[0]
        return None

    def has_results(self) -> bool:
        """检查是否有结果数据"""
        return bool(self.result_data)

    def get_duration_seconds(self) -> Optional[float]:
        """获取执行时长（秒）"""
        if self.execution_time_ms:
            return self.execution_time_ms / 1000.0
        return None