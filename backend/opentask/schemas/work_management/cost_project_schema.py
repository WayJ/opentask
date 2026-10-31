"""成本项目相关 Schema"""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class CostProjectBase(BaseModel):
    """成本项目基础 Schema"""
    name: str = Field(..., min_length=1, max_length=200, description="项目名称")
    code: str = Field(..., min_length=1, max_length=50, description="项目编号")
    description: Optional[str] = Field(None, description="项目描述")
    manager_id: str = Field(..., description="项目经理ID")


class CostProjectCreate(CostProjectBase):
    """创建成本项目 Schema"""
    pass


class CostProjectUpdate(BaseModel):
    """更新成本项目 Schema"""
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    manager_id: Optional[str] = None
    status: Optional[str] = Field(None, pattern="^(active|completed|archived)$")


class CostProjectResponse(CostProjectBase):
    """成本项目响应 Schema"""
    id: str
    status: str
    created_at: datetime
    updated_at: datetime

    # 统计信息（详情时返回）
    total_estimated_hours: Optional[float] = None
    completed_hours: Optional[float] = None
    completion_rate: Optional[float] = None
    high_quality_rate: Optional[float] = None

    class Config:
        from_attributes = True
