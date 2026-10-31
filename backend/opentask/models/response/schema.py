"""
OpenTask统一响应数据模型
用于规范返回给前端的数据结构
"""

from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field
from datetime import datetime
from uuid import UUID

# ==================== 深度搜索流式响应模型 ====================

class TaskUpdateData(BaseModel):
    """任务更新数据"""
    task_name: str = Field(..., description="任务名称")
    task_status: str = Field(..., description="任务状态")
    task_progress: Optional[int] = Field(None, description="任务进度")
    description: Optional[str] = Field(None, description="任务描述")
    timestamp: str = Field(..., description="时间戳")

class ThinkingUpdateData(BaseModel):
    """思考更新数据"""
    message_id: str = Field(..., description="消息ID")
    content: str = Field(..., description="思考内容")
    task_id: Optional[str] = Field(None, description="任务ID")
    is_final: bool = Field(False, description="是否最终消息")
    timestamp: str = Field(..., description="时间戳")

class SearchResultData(BaseModel):
    """搜索结果数据"""
    query: str = Field(..., description="搜索查询")
    results_count: int = Field(0, description="结果数量")
    results: Optional[Dict[str, Any]] = Field(default=None, description="搜索结果数据（包含完整的Genie搜索结果）")
    timestamp: str = Field(..., description="时间戳")

class ReportContentData(BaseModel):
    """报告内容数据"""
    content: str = Field(..., description="报告内容")
    is_final: bool = Field(False, description="是否最终报告")
    report_type: Optional[str] = Field(None, description="报告类型")
    timestamp: str = Field(..., description="时间戳")

class SearchStartedData(BaseModel):
    """搜索开始数据"""
    query: str = Field(..., description="搜索查询内容")
    status: str = Field("started", description="状态")
    workspace_info: Optional[Dict[str, Any]] = Field(None, description="工作空间信息")
    timestamp: str = Field(..., description="时间戳")

class SearchCompletedData(BaseModel):
    """搜索完成数据"""
    status: str = Field("completed", description="状态")
    report_content: Optional[str] = Field(None, description="报告内容")
    search_results_count: int = Field(0, description="搜索结果数量")
    total_time: Optional[float] = Field(None, description="总耗时（秒）")
    timestamp: str = Field(..., description="时间戳")

class ErrorData(BaseModel):
    """错误数据"""
    error: str = Field(..., description="错误信息")
    error_type: Optional[str] = Field(None, description="错误类型")
    details: Optional[Dict[str, Any]] = Field(None, description="错误详情")
    timestamp: str = Field(..., description="时间戳")

class GenieUpdateData(BaseModel):
    """Genie更新数据"""
    display_model: Dict[str, Any] = Field(..., description="Genie显示模型")
    raw_model: Dict[str, Any] = Field(..., description="Genie原始模型")
    timestamp: str = Field(..., description="时间戳")

# ==================== 统一流式响应模型 ====================

class DeepSearchStreamResponse(BaseModel):
    """
    深度搜索流式响应统一模型

    所有deep-search/stream接口返回的数据都使用此模型封装
    """
    type: str = Field(..., description="响应类型")
    conversation_id: str = Field(..., description="会话ID")
    request_id: str = Field(..., description="请求ID")
    data: Dict[str, Any] = Field(..., description="响应数据")
    timestamp: str = Field(..., description="时间戳")

    @classmethod
    def create_task_update(
        cls,
        conversation_id: UUID,
        request_id: str,
        task_name: str,
        task_status: str,
        task_progress: Optional[int] = None,
        description: Optional[str] = None
    ) -> "DeepSearchStreamResponse":
        """创建任务更新响应"""
        return cls(
            type="task_update",
            conversation_id=str(conversation_id),
            request_id=request_id,
            data={
                "task_name": task_name,
                "task_status": task_status,
                "task_progress": task_progress or 0,
                "description": description or "",
                "timestamp": datetime.now().isoformat()
            },
            timestamp=datetime.now().isoformat()
        )

    @classmethod
    def create_thinking_update(
        cls,
        conversation_id: UUID,
        request_id: str,
        message_id: str,
        content: str,
        task_id: Optional[str] = None,
        is_final: bool = False
    ) -> "DeepSearchStreamResponse":
        """创建思考更新响应"""
        return cls(
            type="thinking_update",
            conversation_id=str(conversation_id),
            request_id=request_id,
            data={
                "message_id": message_id,
                "content": content,
                "task_id": task_id,
                "is_final": is_final,
                "timestamp": datetime.now().isoformat()
            },
            timestamp=datetime.now().isoformat()
        )

    @classmethod
    def create_search_result(
        cls,
        conversation_id: UUID,
        request_id: str,
        query: str,
        results: Dict[str, Any]
    ) -> "DeepSearchStreamResponse":
        """创建搜索结果响应"""
        # 计算总的结果数量
        results_count = 0
        if results and "docs" in results:
            for doc_group in results["docs"]:
                results_count += len(doc_group)

        return cls(
            type="search_result",
            conversation_id=str(conversation_id),
            request_id=request_id,
            data={
                "query": query,
                "results_count": results_count,
                "results": results,
                "timestamp": datetime.now().isoformat()
            },
            timestamp=datetime.now().isoformat()
        )

    @classmethod
    def create_report_content(
        cls,
        conversation_id: UUID,
        request_id: str,
        content: str,
        is_final: bool = False,
        report_type: Optional[str] = None
    ) -> "DeepSearchStreamResponse":
        """创建报告内容响应"""
        return cls(
            type="report_content",
            conversation_id=str(conversation_id),
            request_id=request_id,
            data={
                "content": content,
                "is_final": is_final,
                "report_type": report_type,
                "timestamp": datetime.now().isoformat()
            },
            timestamp=datetime.now().isoformat()
        )

    @classmethod
    def create_search_started(
        cls,
        conversation_id: UUID,
        request_id: str,
        query: str,
        workspace_info: Optional[Dict[str, Any]] = None
    ) -> "DeepSearchStreamResponse":
        """创建搜索开始响应"""
        return cls(
            type="search_started",
            conversation_id=str(conversation_id),
            request_id=request_id,
            data={
                "query": query,
                "status": "started",
                "workspace_info": workspace_info or {},
                "timestamp": datetime.now().isoformat()
            },
            timestamp=datetime.now().isoformat()
        )

    @classmethod
    def create_search_completed(
        cls,
        conversation_id: UUID,
        request_id: str,
        report_content: Optional[str] = None,
        search_results_count: int = 0,
        total_time: Optional[float] = None
    ) -> "DeepSearchStreamResponse":
        """创建搜索完成响应"""
        return cls(
            type="search_completed",
            conversation_id=str(conversation_id),
            request_id=request_id,
            data={
                "status": "completed",
                "report_content": report_content or "",
                "search_results_count": search_results_count,
                "total_time": total_time,
                "timestamp": datetime.now().isoformat()
            },
            timestamp=datetime.now().isoformat()
        )

    @classmethod
    def create_error(
        cls,
        conversation_id: UUID,
        request_id: str,
        error: str,
        error_type: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ) -> "DeepSearchStreamResponse":
        """创建错误响应"""
        return cls(
            type="error",
            conversation_id=str(conversation_id),
            request_id=request_id,
            data={
                "error": error,
                "error_type": error_type,
                "details": details or {},
                "timestamp": datetime.now().isoformat()
            },
            timestamp=datetime.now().isoformat()
        )

    @classmethod
    def create_genie_update(
        cls,
        conversation_id: UUID,
        request_id: str,
        display_model: Dict[str, Any],
        raw_model: Dict[str, Any]
    ) -> "DeepSearchStreamResponse":
        """创建Genie更新响应"""
        return cls(
            type="genie_update",
            conversation_id=str(conversation_id),
            request_id=request_id,
            data={
                "display_model": display_model,
                "raw_model": raw_model,
                "timestamp": datetime.now().isoformat()
            },
            timestamp=datetime.now().isoformat()
        )