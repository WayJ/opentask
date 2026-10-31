"""工作安排相关 Schema"""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime, date


class WorkAssignmentBase(BaseModel):
    """工作安排基础 Schema"""
    title: str = Field(..., min_length=1, max_length=200, description="工作内容")
    assignee_id: str = Field(..., description="被分配人ID")
    group_id: str = Field(..., description="所属研发组ID")
    cost_project_id: str = Field(..., description="成本承担项目ID")
    deadline: date = Field(..., description="完成时间要求")
    estimated_hours: float = Field(..., gt=0, le=999, description="工作量（小时）")
    week_start: date = Field(..., description="所属周")
    related_type: Optional[str] = Field(None, pattern="^(requirement|issue)$", description="关联类型")
    related_id: Optional[str] = Field(None, description="关联ID")


class WorkAssignmentCreate(WorkAssignmentBase):
    """创建工作安排 Schema"""
    pass


class WorkAssignmentUpdate(BaseModel):
    """更新工作安排 Schema"""
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    deadline: Optional[date] = None
    estimated_hours: Optional[float] = Field(None, gt=0, le=999)
    status: Optional[str] = Field(None, pattern="^(not_started|in_progress|completed|blocked)$")


class WorkAssignmentResponse(WorkAssignmentBase):
    """工作安排响应 Schema"""
    id: str
    assigner_id: str
    status: str
    quality: str
    created_at: datetime
    updated_at: datetime

    # 延期信息
    is_overdue: bool = False
    overdue_days: int = 0

    class Config:
        from_attributes = True
