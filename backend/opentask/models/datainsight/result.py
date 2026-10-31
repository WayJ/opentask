"""
Analysis Result Model

DataInsight智能体分析结果数据模型
"""

from sqlalchemy import Column, String, Text, DateTime, JSON, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
from typing import Dict, Any, List, Optional

from opentask.models.base import DBModel, UUIDMixin


class AnalysisResult(DBModel, UUIDMixin, kw_only=True):
    """分析结果模型"""

    __tablename__ = "analysis_results"

    # 关联信息
    execution_id: str = Column(
        UUID(as_uuid=True),
        ForeignKey("analysis_executions.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # 结果基本信息
    result_type: str = Column(
        String(50),
        nullable=False,
        index=True
    )  # table, chart, report, insight, file, etc.
    title: str = Column(String(255), nullable=False)
    description: Optional[str] = Column(Text, nullable=True)

    # 结果数据
    data: Dict[str, Any] = Column(
        JSON,
        nullable=False
    )
    metadata: Dict[str, Any] = Column(
        JSON,
        nullable=False,
        default=dict
    )

    # 文件引用
    file_references: List[str] = Column(
        JSON,
        nullable=False,
        default=list
    )

    # 数据统计
    data_size_bytes: Optional[int] = Column(
        "data_size",
        nullable=True
    )
    row_count: Optional[int] = Column(
        nullable=True
    )
    column_count: Optional[int] = Column(
        nullable=True
    )

    # 结果状态
    is_public: bool = Column(
        nullable=False,
        default=False
    )
    is_cached: bool = Column(
        nullable=False,
        default=False
    )
    cache_key: Optional[str] = Column(
        String(255),
        nullable=True,
        unique=True
    )

    # 访问统计
    access_count: int = Column(
        nullable=False,
        default=0
    )
    last_accessed_at: Optional[datetime] = Column(
        DateTime(timezone=True),
        nullable=True
    )

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

    # 关系
    execution = relationship(
        "AnalysisExecution",
        back_populates="results"
    )

    def __repr__(self) -> str:
        return f"<AnalysisResult(id={self.id}, type={self.result_type}, title={self.title})>"

    def to_dict(self) -> dict:
        """转换为字典格式"""
        return {
            "id": str(self.id),
            "execution_id": str(self.execution_id),
            "result_type": self.result_type,
            "title": self.title,
            "description": self.description,
            "data": self.data,
            "metadata": self.metadata,
            "file_references": self.file_references,
            "data_size_bytes": self.data_size_bytes,
            "row_count": self.row_count,
            "column_count": self.column_count,
            "is_public": self.is_public,
            "is_cached": self.is_cached,
            "cache_key": self.cache_key,
            "access_count": self.access_count,
            "last_accessed_at": self.last_accessed_at.isoformat() if self.last_accessed_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def is_table_result(self) -> bool:
        """检查是否为表格结果"""
        return self.result_type == "table"

    def is_chart_result(self) -> bool:
        """检查是否为图表结果"""
        return self.result_type == "chart"

    def is_report_result(self) -> bool:
        """检查是否为报告结果"""
        return self.result_type == "report"

    def is_insight_result(self) -> bool:
        """检查是否为洞察结果"""
        return self.result_type == "insight"

    def add_file_reference(self, file_id: str) -> None:
        """添加文件引用"""
        if self.file_references:
            self.file_references.append(file_id)
        else:
            self.file_references = [file_id]

    def remove_file_reference(self, file_id: str) -> None:
        """移除文件引用"""
        if self.file_references and file_id in self.file_references:
            self.file_references.remove(file_id)

    def update_metadata(self, key: str, value: Any) -> None:
        """更新元数据"""
        if self.metadata:
            self.metadata[key] = value
        else:
            self.metadata = {key: value}

    def increment_access_count(self) -> None:
        """增加访问次数"""
        self.access_count += 1
        self.last_accessed_at = datetime.utcnow()

    def calculate_data_size(self) -> None:
        """计算数据大小"""
        import json
        if self.data:
            data_str = json.dumps(self.data)
            self.data_size_bytes = len(data_str.encode('utf-8'))

    def set_cache_key(self, key: str) -> None:
        """设置缓存键"""
        self.cache_key = key
        self.is_cached = True

    def clear_cache(self) -> None:
        """清除缓存"""
        self.cache_key = None
        self.is_cached = False

    def get_summary(self) -> Dict[str, Any]:
        """获取结果摘要"""
        summary = {
            "type": self.result_type,
            "title": self.title,
            "description": self.description,
            "created_at": self.created_at.isoformat(),
        }

        if self.is_table_result():
            summary.update({
                "rows": self.row_count,
                "columns": self.column_count,
                "size_mb": round(self.data_size_bytes / (1024 * 1024), 2) if self.data_size_bytes else None
            })

        if self.is_chart_result():
            chart_config = self.metadata.get("chart_config", {})
            summary.update({
                "chart_type": chart_config.get("type"),
                "has_animation": chart_config.get("animated", False)
            })

        return summary

    def can_access(self, user_id: str) -> bool:
        """检查用户是否可以访问此结果"""
        # 如果是公开结果，任何人都可以访问
        if self.is_public:
            return True

        # TODO: 实现基于权限的访问控制
        # 这里可以根据execution_id关联的请求用户来判断权限
        return True

    def validate_data_structure(self) -> bool:
        """验证数据结构是否有效"""
        if not self.data:
            return False

        # 根据结果类型验证数据结构
        if self.is_table_result():
            return self._validate_table_data()
        elif self.is_chart_result():
            return self._validate_chart_data()
        elif self.is_report_result():
            return self._validate_report_data()

        return True

    def _validate_table_data(self) -> bool:
        """验证表格数据结构"""
        required_fields = ["columns", "rows"]
        return all(field in self.data for field in required_fields)

    def _validate_chart_data(self) -> bool:
        """验证图表数据结构"""
        required_fields = ["data", "config"]
        return all(field in self.data for field in required_fields)

    def _validate_report_data(self) -> bool:
        """验证报告数据结构"""
        required_fields = ["content"]
        return all(field in self.data for field in required_fields)