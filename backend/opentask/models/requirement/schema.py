"""需求模块 Pydantic Schema"""
from datetime import datetime
from typing import Any
from pydantic import BaseModel, Field

from opentask.models.requirement.enums import (
    RequirementStatus,
    Priority,
    EventType,
    MergeStatus,
    JobStatus,
    JobType,
)


# ============================================================================
# 设计文档相关 Schema（前置引用）
# ============================================================================


class DocumentSummary(BaseModel):
    """文档摘要（用于嵌入到其他实体响应中）"""
    id: str
    file_name: str | None = None
    status: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ============================================================================
# 需求相关 Schema
# ============================================================================


class RequirementBase(BaseModel):
    """需求基础 Schema"""
    title: str = Field(..., description="需求标题")
    code: str | None = Field(None, description="需求编码")
    description: str | None = Field(None, description="需求描述")
    priority: Priority | None = Field(None, description="优先级")
    tags: list[str] = Field(default_factory=list, description="标签列表")


class RequirementCreate(RequirementBase):
    """创建需求 Schema"""
    project_id: str | None = Field(None, description="所属项目 ID")
    created_by: str | None = Field(None, description="创建者 ID")


class RequirementUpdate(BaseModel):
    """更新需求 Schema"""
    title: str | None = None
    description: str | None = None
    status: RequirementStatus | None = None
    priority: Priority | None = None
    tags: list[str] | None = None
    assignee_id: str | None = None
    project_id: str | None = None


class RequirementResponse(RequirementBase):
    """需求响应 Schema"""
    id: str
    code: str
    status: RequirementStatus
    created_at: datetime
    updated_at: datetime
    created_by: str | None
    assignee_id: str | None
    project_id: str | None = Field(None, description="所属项目 ID")
    project_name: str | None = Field(None, description="所属项目名称")
    # 关联文档（轻量级摘要）
    documents: list[DocumentSummary] = Field(default_factory=list, description="关联的设计文档")

    class Config:
        from_attributes = True


class RequirementWithEvents(RequirementResponse):
    """包含事件的需求响应 Schema"""
    events: list["EventResponse"] = []


# ============================================================================
# 事件相关 Schema
# ============================================================================


class EventBase(BaseModel):
    """事件基础 Schema"""
    type: EventType
    data: dict[str, Any] = Field(default_factory=dict)
    actor: str | None = None
    reasoning: str | None = None


class EventCreate(EventBase):
    """创建事件 Schema"""
    requirement_id: str


class EventResponse(EventBase):
    """事件响应 Schema"""
    id: str
    requirement_id: str
    timestamp: datetime
    snapshot: dict[str, Any] | None = None

    class Config:
        from_attributes = True


# ============================================================================
# 项目/仓库相关 Schema
# ============================================================================


class ProjectBase(BaseModel):
    """项目基础 Schema"""
    name: str = Field(..., description="项目名称")
    description: str | None = Field(None, description="项目描述")


class ProjectCreate(ProjectBase):
    """创建项目 Schema"""
    pass


class ProjectResponse(ProjectBase):
    """项目响应 Schema"""
    id: str
    is_active: bool
    created_at: datetime
    updated_at: datetime
    starts_at: datetime | None = None
    target_date: datetime | None = None

    class Config:
        from_attributes = True


class RepoConfigBase(BaseModel):
    """仓库配置基础 Schema"""
    name: str = Field(..., description="仓库名称")
    url: str = Field(..., description="Git 仓库 URL")
    main_branch: str = Field(default="main", description="主分支名称")


class RepoConfigCreate(RepoConfigBase):
    """创建仓库配置 Schema"""
    project_id: str


class RepoConfigResponse(RepoConfigBase):
    """仓库配置响应 Schema"""
    id: int
    project_id: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class RequirementRepoCreate(BaseModel):
    """创建需求-仓库关联 Schema"""
    requirement_id: str
    repo_id: int


class RequirementRepoResponse(BaseModel):
    """需求-仓库关联响应 Schema"""
    id: str
    requirement_id: str
    repo_id: int
    branch: str | None = None
    pr_url: str | None = None
    merge_status: MergeStatus | None = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ============================================================================
# 用户相关 Schema
# ============================================================================


class UserInfo(BaseModel):
    """用户基本信息"""
    id: str
    name: str | None = Field(None, description="用户名")
    sso_name: str | None = Field(None, description="SSO 用户名称")
    sso_account: str | None = Field(None, description="SSO 账号")

    model_config = {"from_attributes": True}


# ============================================================================
# 评论相关 Schema
# ============================================================================


class CommentBase(BaseModel):
    """评论基础 Schema"""
    content: str = Field(..., description="评论内容")


class CommentCreate(CommentBase):
    """创建评论 Schema"""
    requirement_id: str
    user_id: str | None = None


class CommentResponse(CommentBase):
    """评论响应 Schema"""
    id: str
    requirement_id: str
    user_id: str | None = None
    user_info: UserInfo | None = Field(None, description="用户信息")
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ============================================================================
# 队列任务相关 Schema
# ============================================================================


class QueueJobBase(BaseModel):
    """队列任务基础 Schema"""
    type: JobType
    data: dict[str, Any] | None = None


class QueueJobCreate(QueueJobBase):
    """创建队列任务 Schema"""
    requirement_id: str | None = None
    max_attempts: int = 3


class QueueJobResponse(QueueJobBase):
    """队列任务响应 Schema"""
    id: str
    requirement_id: str | None = None
    status: JobStatus
    result: dict[str, Any] | None = None
    error: str | None = None
    attempts: int
    max_attempts: int
    created_at: datetime
    started_at: datetime | None = None
    completed_at: datetime | None = None

    class Config:
        from_attributes = True


# ============================================================================
# 统计相关 Schema
# ============================================================================


class RequirementStatistics(BaseModel):
    """需求统计 Schema"""
    total: int
    by_status: dict[str, int]
    by_priority: dict[str, int]


class RequirementListResponse(BaseModel):
    """需求列表响应 Schema"""
    data: list[RequirementResponse]
    total: int
    page: int
    page_size: int


class TimelineResponse(BaseModel):
    """时间线响应 Schema"""
    requirement_id: str
    events: list[EventResponse]
    time_in_states: dict[str, int]  # 各状态耗时（毫秒）


# ============================================================================
# 分配相关 Schema
# ============================================================================


class AssignRequest(BaseModel):
    """分配需求 Schema"""
    assignee_id: str


# 更新前向引用
RequirementWithEvents.model_rebuild()
