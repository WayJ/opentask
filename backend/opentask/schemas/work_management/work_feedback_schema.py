"""工作反馈相关 Schema"""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime, date


class WorkFeedbackBase(BaseModel):
    """工作反馈基础 Schema"""
    assignment_id: Optional[str] = Field(None, description="关联工作安排ID（计划内必填）")
    feedback_date: date = Field(..., description="反馈日期")
    content: Optional[str] = Field(None, description="反馈内容")
    status: str = Field(..., pattern="^(not_started|in_progress|completed|blocked)$", description="工作状态")
    is_planned: bool = Field(True, description="是否计划内")
    unplanned_type: Optional[str] = Field(None, pattern="^(issue_created|issue_resolved|req_created|req_completed|other)$")
    unplanned_related_id: Optional[str] = Field(None)


class WorkFeedbackCreate(WorkFeedbackBase):
    """创建工作反馈 Schema"""
    pass


class WorkFeedbackUpdate(BaseModel):
    """更新工作反馈 Schema"""
    content: Optional[str] = None
    status: Optional[str] = Field(None, pattern="^(not_started|in_progress|completed|blocked)$")


class WorkFeedbackResponse(WorkFeedbackBase):
    """工作反馈响应 Schema"""
    id: str
    user_id: str
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class UnplannedWorkItem(BaseModel):
    """计划外工作项"""
    id: str
    type: str
    title: str
    status: str
    updated_at: datetime


class MyWeeklyWorkResponse(BaseModel):
    """我的周工作响应 Schema"""
    current_week: dict
    overdue: List["WorkAssignmentResponse"]
    summary: dict
