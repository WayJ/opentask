"""
DataInsight Pydantic Schemas

DataInsight智能体的Pydantic数据模式定义
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
from pydantic import BaseModel, Field
from enum import Enum


class SessionStatus(str, Enum):
    """会话状态枚举"""
    ACTIVE = "active"
    COMPLETED = "completed"
    ARCHIVED = "archived"


class RequestStatus(str, Enum):
    """请求状态枚举"""
    PENDING = "pending"
    ANALYZING = "analyzing"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ExecutionStatus(str, Enum):
    """执行状态枚举"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ResultType(str, Enum):
    """结果类型枚举"""
    TABLE = "table"
    CHART = "chart"
    REPORT = "report"
    INSIGHT = "insight"
    FILE = "file"
    METRIC = "metric"


class ToolType(str, Enum):
    """工具类型枚举"""
    SQL_QUERY = "sql_query"
    STATISTICAL_ANALYSIS = "statistical_analysis"
    DATA_CLEANING = "data_cleaning"
    FEATURE_ENGINEERING = "feature_engineering"
    VISUALIZATION = "visualization"
    REPORT_GENERATION = "report_generation"
    PREDICTIVE_MODELING = "predictive_modeling"


class ReportType(str, Enum):
    """报告类型枚举"""
    COMPREHENSIVE = "comprehensive"
    EXECUTIVE_SUMMARY = "executive_summary"
    DETAILED_ANALYSIS = "detailed_analysis"
    DASHBOARD = "dashboard"
    CUSTOM = "custom"


class DataInsightSessionBase(BaseModel):
    """会话基础模式"""
    title: str = Field(..., description="会话标题", min_length=1, max_length=255)
    description: Optional[str] = Field(None, description="会话描述", max_length=1000)
    context: Dict[str, Any] = Field(default_factory=dict, description="会话上下文")


class DataInsightSessionCreate(DataInsightSessionBase):
    """创建会话模式"""
    user_id: str = Field(..., description="用户ID")


class DataInsightSessionUpdate(BaseModel):
    """更新会话模式"""
    title: Optional[str] = Field(None, description="会话标题", min_length=1, max_length=255)
    description: Optional[str] = Field(None, description="会话描述", max_length=1000)
    status: Optional[SessionStatus] = Field(None, description="会话状态")
    context: Optional[Dict[str, Any]] = Field(None, description="会话上下文")


class DataInsightSessionOut(DataInsightSessionBase):
    """会话输出模式"""
    id: str = Field(..., description="会话ID")
    user_id: str = Field(..., description="用户ID")
    status: SessionStatus = Field(..., description="会话状态")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")
    ended_at: Optional[datetime] = Field(None, description="结束时间")
    request_count: Optional[int] = Field(None, description="请求数量")
    last_activity: Optional[datetime] = Field(None, description="最后活动时间")

    class Config:
        from_attributes = True


class AnalysisRequestBase(BaseModel):
    """分析请求基础模式"""
    user_input: str = Field(..., description="用户输入", min_length=1, max_length=5000)
    connection_id: Optional[str] = Field(None, description="数据库连接ID")
    files: List[str] = Field(default_factory=list, description="上传文件列表")
    context: Dict[str, Any] = Field(default_factory=dict, description="请求上下文")


class AnalysisRequestCreate(AnalysisRequestBase):
    """创建分析请求模式"""
    session_id: str = Field(..., description="会话ID")


class AnalysisRequestUpdate(BaseModel):
    """更新分析请求模式"""
    status: Optional[RequestStatus] = Field(None, description="请求状态")
    intent_analysis: Optional[Dict[str, Any]] = Field(None, description="意图分析结果")
    selected_tools: Optional[List[Dict[str, Any]]] = Field(None, description="选择的工具")
    execution_plan: Optional[Dict[str, Any]] = Field(None, description="执行计划")


class AnalysisRequestOut(AnalysisRequestBase):
    """分析请求输出模式"""
    id: str = Field(..., description="请求ID")
    session_id: str = Field(..., description="会话ID")
    status: RequestStatus = Field(..., description="请求状态")
    intent_analysis: Optional[Dict[str, Any]] = Field(None, description="意图分析结果")
    selected_tools: List[Dict[str, Any]] = Field(default_factory=list, description="选择的工具")
    execution_plan: Optional[Dict[str, Any]] = Field(None, description="执行计划")
    processing_time_ms: Optional[int] = Field(None, description="处理时间（毫秒）")
    total_executions: int = Field(default=0, description="总执行次数")
    successful_executions: int = Field(default=0, description="成功执行次数")
    created_at: datetime = Field(..., description="创建时间")
    started_at: Optional[datetime] = Field(None, description="开始时间")
    completed_at: Optional[datetime] = Field(None, description="完成时间")
    success_rate: float = Field(default=0.0, description="成功率")

    class Config:
        from_attributes = True


class AnalysisExecutionBase(BaseModel):
    """分析执行基础模式"""
    tool_name: str = Field(..., description="工具名称", min_length=1, max_length=100)
    tool_type: ToolType = Field(..., description="工具类型")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="工具参数")


class AnalysisExecutionCreate(AnalysisExecutionBase):
    """创建分析执行模式"""
    request_id: str = Field(..., description="请求ID")


class AnalysisExecutionUpdate(BaseModel):
    """更新分析执行模式"""
    status: Optional[ExecutionStatus] = Field(None, description="执行状态")
    result_data: Optional[Dict[str, Any]] = Field(None, description="执行结果")
    error_message: Optional[str] = Field(None, description="错误信息")
    confidence_score: Optional[float] = Field(None, description="置信度分数", ge=0.0, le=1.0)
    insights: Optional[List[str]] = Field(None, description="洞察列表")
    visualizations: Optional[List[Dict[str, Any]]] = Field(None, description="可视化配置")
    metrics: Optional[Dict[str, Any]] = Field(None, description="执行指标")


class AnalysisExecutionOut(AnalysisExecutionBase):
    """分析执行输出模式"""
    id: str = Field(..., description="执行ID")
    request_id: str = Field(..., description="请求ID")
    status: ExecutionStatus = Field(..., description="执行状态")
    result_data: Optional[Dict[str, Any]] = Field(None, description="执行结果")
    error_message: Optional[str] = Field(None, description="错误信息")
    execution_time_ms: Optional[int] = Field(None, description="执行时间（毫秒）")
    confidence_score: Optional[float] = Field(None, description="置信度分数")
    insights: List[str] = Field(default_factory=list, description="洞察列表")
    visualizations: List[Dict[str, Any]] = Field(default_factory=list, description="可视化配置")
    metrics: Dict[str, Any] = Field(default_factory=dict, description="执行指标")
    created_at: datetime = Field(..., description="创建时间")
    started_at: Optional[datetime] = Field(None, description="开始时间")
    completed_at: Optional[datetime] = Field(None, description="完成时间")
    duration_seconds: Optional[float] = Field(None, description="执行时长（秒）")

    class Config:
        from_attributes = True


class AnalysisResultBase(BaseModel):
    """分析结果基础模式"""
    result_type: ResultType = Field(..., description="结果类型")
    title: str = Field(..., description="结果标题", min_length=1, max_length=255)
    description: Optional[str] = Field(None, description="结果描述", max_length=1000)
    data: Dict[str, Any] = Field(..., description="结果数据")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="结果元数据")
    file_references: List[str] = Field(default_factory=list, description="文件引用")


class AnalysisResultCreate(AnalysisResultBase):
    """创建分析结果模式"""
    execution_id: str = Field(..., description="执行ID")


class AnalysisResultUpdate(BaseModel):
    """更新分析结果模式"""
    title: Optional[str] = Field(None, description="结果标题", min_length=1, max_length=255)
    description: Optional[str] = Field(None, description="结果描述", max_length=1000)
    data: Optional[Dict[str, Any]] = Field(None, description="结果数据")
    metadata: Optional[Dict[str, Any]] = Field(None, description="结果元数据")
    file_references: Optional[List[str]] = Field(None, description="文件引用")
    is_public: Optional[bool] = Field(None, description="是否公开")


class AnalysisResultOut(AnalysisResultBase):
    """分析结果输出模式"""
    id: str = Field(..., description="结果ID")
    execution_id: str = Field(..., description="执行ID")
    data_size_bytes: Optional[int] = Field(None, description="数据大小（字节）")
    row_count: Optional[int] = Field(None, description="行数")
    column_count: Optional[int] = Field(None, description="列数")
    is_public: bool = Field(default=False, description="是否公开")
    is_cached: bool = Field(default=False, description="是否缓存")
    cache_key: Optional[str] = Field(None, description="缓存键")
    access_count: int = Field(default=0, description="访问次数")
    last_accessed_at: Optional[datetime] = Field(None, description="最后访问时间")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")
    summary: Optional[Dict[str, Any]] = Field(None, description="结果摘要")

    class Config:
        from_attributes = True


class AnalysisReportBase(BaseModel):
    """分析报告基础模式"""
    title: str = Field(..., description="报告标题", min_length=1, max_length=255)
    summary: Optional[str] = Field(None, description="报告摘要", max_length=2000)
    content: Dict[str, Any] = Field(..., description="报告内容")
    report_type: ReportType = Field(default=ReportType.COMPREHENSIVE, description="报告类型")
    format: str = Field(default="markdown", description="报告格式", max_length=20)


class AnalysisReportCreate(AnalysisReportBase):
    """创建分析报告模式"""
    session_id: str = Field(..., description="会话ID")


class AnalysisReportUpdate(BaseModel):
    """更新分析报告模式"""
    title: Optional[str] = Field(None, description="报告标题", min_length=1, max_length=255)
    summary: Optional[str] = Field(None, description="报告摘要", max_length=2000)
    content: Optional[Dict[str, Any]] = Field(None, description="报告内容")
    is_published: Optional[bool] = Field(None, description="是否发布")


class AnalysisReportOut(AnalysisReportBase):
    """分析报告输出模式"""
    id: str = Field(..., description="报告ID")
    session_id: str = Field(..., description="会话ID")
    insights: List[str] = Field(default_factory=list, description="关键洞察")
    recommendations: List[str] = Field(default_factory=list, description="建议")
    key_metrics: Dict[str, Any] = Field(default_factory=dict, description="关键指标")
    visualizations: List[Dict[str, Any]] = Field(default_factory=list, description="可视化")
    file_path: Optional[str] = Field(None, description="文件路径")
    is_published: bool = Field(default=False, description="是否发布")
    published_at: Optional[datetime] = Field(None, description="发布时间")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")

    class Config:
        from_attributes = True


class AnalysisToolOut(BaseModel):
    """分析工具输出模式"""
    id: str = Field(..., description="工具ID")
    name: str = Field(..., description="工具名称")
    display_name: str = Field(..., description="显示名称")
    description: Optional[str] = Field(None, description="工具描述")
    tool_type: ToolType = Field(..., description="工具类型")
    capabilities: List[str] = Field(default_factory=list, description="工具能力")
    parameters_schema: Optional[Dict[str, Any]] = Field(None, description="参数模式")
    priority: int = Field(default=0, description="优先级")
    is_active: bool = Field(default=True, description="是否活跃")
    version: str = Field(default="1.0.0", description="版本号")

    class Config:
        from_attributes = True


class IntentPatternOut(BaseModel):
    """意图模式输出模式"""
    id: str = Field(..., description="模式ID")
    pattern_name: str = Field(..., description="模式名称")
    keywords: List[str] = Field(default_factory=list, description="关键词")
    intent_type: str = Field(..., description="意图类型")
    confidence_threshold: float = Field(default=0.7, description="置信度阈值")
    tool_preferences: List[str] = Field(default_factory=list, description="工具偏好")
    example_queries: List[str] = Field(default_factory=list, description="示例查询")
    usage_count: int = Field(default=0, description="使用次数")
    success_rate: float = Field(default=0.0, description="成功率")

    class Config:
        from_attributes = True


# 分页响应模式
class PaginatedSessionList(BaseModel):
    """分页会话列表"""
    items: List[DataInsightSessionOut]
    total: int = Field(..., description="总数")
    page: int = Field(..., description="当前页")
    size: int = Field(..., description="每页大小")
    pages: int = Field(..., description="总页数")


class PaginatedRequestList(BaseModel):
    """分页请求列表"""
    items: List[AnalysisRequestOut]
    total: int = Field(..., description="总数")
    page: int = Field(..., description="当前页")
    size: int = Field(..., description="每页大小")
    pages: int = Field(..., description="总页数")


class PaginatedResultList(BaseModel):
    """分页结果列表"""
    items: List[AnalysisResultOut]
    total: int = Field(..., description="总数")
    page: int = Field(..., description="当前页")
    size: int = Field(..., description="每页大小")
    pages: int = Field(..., description="总页数")


# 统计信息模式
class SessionStatistics(BaseModel):
    """会话统计信息"""
    total_sessions: int = Field(..., description="总会话数")
    active_sessions: int = Field(..., description="活跃会话数")
    completed_sessions: int = Field(..., description="完成会话数")
    archived_sessions: int = Field(..., description="归档会话数")
    average_requests_per_session: float = Field(..., description="平均每会话请求数")
    total_requests: int = Field(..., description="总请求数")


class RequestStatistics(BaseModel):
    """请求统计信息"""
    total_requests: int = Field(..., description="总请求数")
    pending_requests: int = Field(..., description="待处理请求数")
    executing_requests: int = Field(..., description="执行中请求数")
    completed_requests: int = Field(..., description="完成请求数")
    failed_requests: int = Field(..., description="失败请求数")
    success_rate: float = Field(..., description="成功率")
    average_processing_time_ms: float = Field(..., description="平均处理时间（毫秒）")


class ToolStatistics(BaseModel):
    """工具统计信息"""
    tool_name: str = Field(..., description="工具名称")
    total_executions: int = Field(..., description="总执行次数")
    successful_executions: int = Field(..., description="成功执行次数")
    failed_executions: int = Field(..., description="失败执行次数")
    success_rate: float = Field(..., description="成功率")
    average_execution_time_ms: float = Field(..., description="平均执行时间（毫秒）")
    average_confidence_score: float = Field(..., description="平均置信度分数")


# 实时事件模式
class SessionEvent(BaseModel):
    """会话事件"""
    event_type: str = Field(..., description="事件类型")
    session_id: str = Field(..., description="会话ID")
    user_id: str = Field(..., description="用户ID")
    data: Optional[Dict[str, Any]] = Field(None, description="事件数据")
    timestamp: datetime = Field(..., description="事件时间")


class RequestEvent(BaseModel):
    """请求事件"""
    event_type: str = Field(..., description="事件类型")
    request_id: str = Field(..., description="请求ID")
    session_id: str = Field(..., description="会话ID")
    user_id: str = Field(..., description="用户ID")
    data: Optional[Dict[str, Any]] = Field(None, description="事件数据")
    timestamp: datetime = Field(..., description="事件时间")


class ExecutionEvent(BaseModel):
    """执行事件"""
    event_type: str = Field(..., description="事件类型")
    execution_id: str = Field(..., description="执行ID")
    request_id: str = Field(..., description="请求ID")
    tool_name: str = Field(..., description="工具名称")
    data: Optional[Dict[str, Any]] = Field(None, description="事件数据")
    timestamp: datetime = Field(..., description="事件时间")