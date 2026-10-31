"""Dashboard 数据 Schema"""
from typing import Optional
from pydantic import BaseModel, Field


class StatusDistribution(BaseModel):
    """状态分布"""
    status: str = Field(..., description="状态值")
    count: int = Field(..., description="数量")


class TypeDistribution(BaseModel):
    """类型分布"""
    type: str = Field(..., description="类型值")
    count: int = Field(..., description="数量")


class PriorityDistribution(BaseModel):
    """优先级分布"""
    priority: str = Field(..., description="优先级")
    count: int = Field(..., description="数量")


class TrendDataPoint(BaseModel):
    """趋势数据点"""
    date: str = Field(..., description="日期 YYYY-MM-DD")
    requirement_count: int = Field(0, description="需求数量")
    issue_count: int = Field(0, description="Issue数量")


class StatCard(BaseModel):
    """统计卡片数据"""
    total: int = Field(0, description="总数")
    open_count: int = Field(0, description="待处理")
    in_progress_count: int = Field(0, description="进行中")
    completed_count: int = Field(0, description="已完成")


class RecentActivityItem(BaseModel):
    """最近动态项"""
    id: str = Field(..., description="ID")
    type: str = Field(..., description="类型: requirement/issue")
    code: str = Field(..., description="编号")
    title: str = Field(..., description="标题")
    status: str = Field(..., description="状态")
    updated_at: str = Field(..., description="更新时间")


class DashboardOverview(BaseModel):
    """看板总览数据"""
    requirements: StatCard = Field(..., description="需求统计")
    issues: StatCard = Field(..., description="Issue统计")
    requirement_by_status: list[StatusDistribution] = Field(default_factory=list, description="需求状态分布")
    requirement_by_priority: list[PriorityDistribution] = Field(default_factory=list, description="需求优先级分布")
    issue_by_status: list[StatusDistribution] = Field(default_factory=list, description="Issue状态分布")
    issue_by_type: list[TypeDistribution] = Field(default_factory=list, description="Issue类型分布")
    issue_by_priority: list[PriorityDistribution] = Field(default_factory=list, description="Issue优先级分布")
    trend: list[TrendDataPoint] = Field(default_factory=list, description="近30天趋势")
    recent_activities: list[RecentActivityItem] = Field(default_factory=list, description="最近动态")


class DashboardOverviewResponse(BaseModel):
    """看板总览响应"""
    code: int = Field(200, description="状态码")
    message: str = Field("success", description="消息")
    data: Optional[DashboardOverview] = Field(None, description="数据")
    timestamp: int = Field(0, description="时间戳")
