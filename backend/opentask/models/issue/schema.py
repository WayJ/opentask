"""Issue 相关的 Pydantic Schemas"""
from datetime import datetime
from typing import Optional, List, Any
from pydantic import BaseModel, Field, ConfigDict, field_validator


from .enums import IssueType, IssueStatus, IssuePriority, CommentType, RelationType, TimelineAction


# ============================================================================
# Common Schemas
# ============================================================================

class UserInfo(BaseModel):
    """用户基本信息"""
    id: str
    name: Optional[str] = Field(None, description="用户名")
    sso_name: Optional[str] = Field(None, description="SSO 用户名称")
    sso_account: Optional[str] = Field(None, description="SSO 账号")

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        # 确保所有字段都序列化，即使为 None
        ser_json_timedelta='iso8601',
        use_enum_values=False
    )


# ============================================================================
# Issue Schemas
# ============================================================================

class IssueBase(BaseModel):
    """Issue 基础 Schema"""
    title: str = Field(..., min_length=1, max_length=255, description="标题")
    description: Optional[str] = Field(None, description="描述")
    type: IssueType = Field(default=IssueType.BUG, description="类型")
    status: IssueStatus = Field(default=IssueStatus.OPEN, description="状态")
    priority: IssuePriority = Field(default=IssuePriority.MEDIUM, description="优先级")
    project_id: Optional[str] = Field(None, description="项目 ID")
    task_id: Optional[str] = Field(None, description="任务 ID")
    requirement_id: Optional[str] = Field(None, description="需求 ID")
    assignee_id: Optional[str] = Field(None, description="负责人 ID")
    reporter_id: Optional[str] = Field(None, description="报告人 ID [可选：默认为当前用户]")
    position: Optional[int] = Field(None, description="排序位置")
    due_date: Optional[datetime] = Field(None, description="截止日期")
    start_date: Optional[datetime] = Field(None, description="E73：计划开始日")
    estimated_hours: Optional[float] = Field(None, ge=0, description="预估工时")
    actual_hours: Optional[float] = Field(None, ge=0, description="实际工时")
    parent_issue_id: Optional[str] = Field(None, description="父 Issue ID（一等公民子 Issue）")
    cycle_id: Optional[str] = Field(None, description="所属 Cycle ID")
    estimate_points: Optional[float] = Field(None, ge=0, description="故事点估算（可选）")
    milestone_id: Optional[str] = Field(None, description="所属里程碑 ID")


class IssueCreate(IssueBase):
    """创建 Issue Schema"""
    template_id: Optional[str] = Field(None, description="E9-S2：应用工作区 Issue 模板")
    assignee_ids: Optional[List[str]] = Field(
        None, description="E71: ordered assignees; first=primary (mirrors assignee_id)"
    )


class IssueDuplicateRequest(BaseModel):
    """E75: optional overrides for POST /api/issues/{id}/duplicate"""
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    project_id: Optional[str] = None
    cycle_id: Optional[str] = None
    parent_issue_id: Optional[str] = None
    assignee_ids: Optional[List[str]] = Field(
        None, description="Replace assignees on the copy; omit to copy source"
    )


class IssueUpdate(BaseModel):
    """更新 Issue Schema"""
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    type: Optional[IssueType] = None
    status: Optional[IssueStatus] = None
    priority: Optional[IssuePriority] = None
    project_id: Optional[str] = None
    task_id: Optional[str] = None
    requirement_id: Optional[str] = None
    assignee_id: Optional[str] = None
    assignee_ids: Optional[List[str]] = Field(
        None, description="E71: replace ordered assignees; first=primary"
    )
    reporter_id: Optional[str] = None
    position: Optional[int] = None
    due_date: Optional[datetime] = None
    start_date: Optional[datetime] = None
    estimated_hours: Optional[float] = None
    actual_hours: Optional[float] = None
    parent_issue_id: Optional[str] = None
    cycle_id: Optional[str] = None
    estimate_points: Optional[float] = None
    milestone_id: Optional[str] = None


class ProjectInfo(BaseModel):
    """项目基本信息"""
    id: str
    name: str
    description: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)



class TagBrief(BaseModel):
    """Issue 上的轻量标签（E7-S1 groupBy / 详情）"""
    id: int
    name: str
    color: str = "#3b82f6"
    group_id: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class IssueChildSummary(BaseModel):
    """子 Issue 轻量摘要"""
    id: str
    issue_code: str
    title: str
    status: str

    model_config = ConfigDict(from_attributes=True)


class ChildProgress(BaseModel):
    """E70: direct-child progress rollup"""
    total: int
    done: int
    open: int
    percent: Optional[int] = None
    byStatus: Optional[dict] = None


class IssueResponse(IssueBase):
    """Issue 响应 Schema"""
    id: str
    issue_code: str
    view_count: int
    comment_count: int
    attachment_count: int
    started_at: Optional[datetime]
    resolved_at: Optional[datetime]
    closed_at: Optional[datetime]
    is_deleted: bool
    created_at: datetime
    updated_at: datetime
    created_by: Optional[str]
    updated_by: Optional[str]
    project: Optional[ProjectInfo] = Field(None, description="关联项目")
    assignee: Optional[UserInfo] = Field(None, description="负责人信息")
    assignees: Optional[List[UserInfo]] = Field(
        None, description="E71: ordered assignees (first=primary)"
    )
    reporter: Optional[UserInfo] = Field(None, description="报告人信息")
    children: Optional[List[IssueChildSummary]] = Field(
        None, description="子 Issue 摘要（详情接口填充）"
    )
    childProgress: Optional[ChildProgress] = Field(
        None, description="E70: 直接子问题进度汇总（详情默认；列表 ?include=childProgress）"
    )
    triage_status: Optional[str] = Field(None, description="pending|null triage 队列状态")

    model_config = ConfigDict(from_attributes=True)

    @field_validator('assignee', 'reporter', mode='before')
    @classmethod
    def convert_user_model_to_info(cls, v: Any) -> Optional[UserInfo]:
        """将 UserModel 转换为 UserInfo"""
        if v is None:
            return None
        if isinstance(v, UserInfo):
            return v
        # 如果是 UserModel 对象或其他对象，提取 id、name、sso_name、sso_account
        if hasattr(v, 'id'):
            user_id = str(v.id) if v.id else None
            user_name = getattr(v, 'name', None)
            sso_name = getattr(v, 'sso_name', None)
            sso_account = getattr(v, 'sso_account', None)
            if user_id:
                return UserInfo(
                    id=user_id,
                    name=user_name,
                    sso_name=sso_name,
                    sso_account=sso_account
                )
        return None


class IssueListResponse(BaseModel):
    """Issue 列表响应 Schema"""
    total: int = Field(..., description="总数")
    items: List[IssueResponse] = Field(..., description="Issue 列表")


# ============================================================================
# Issue Comment Schemas
# ============================================================================

class IssueCommentBase(BaseModel):
    """评论基础 Schema"""
    content: str = Field(..., min_length=1, description="评论内容")
    parent_id: Optional[str] = Field(None, description="父评论 ID")
    comment_type: str = Field(default="comment", description="评论类型")  # 改为字符串类型
    meta_data: Optional[dict] = Field(None, description="元数据")


class IssueCommentRequest(BaseModel):
    """添加评论请求 Schema"""
    content: str = Field(..., min_length=1, max_length=500, description="评论内容（1-500字符）")
    parent_id: Optional[str] = Field(None, description="父评论 ID")


class IssueCommentCreate(IssueCommentBase):
    """创建评论 Schema"""
    issue_id: str = Field(..., description="Issue ID")
    user_id: str = Field(..., description="用户 ID")


class IssueCommentUpdate(BaseModel):
    """更新评论 Schema"""
    content: Optional[str] = Field(None, min_length=1, max_length=500)


class IssueCommentResponse(IssueCommentBase):
    """评论响应 Schema"""
    id: str
    issue_id: str
    user_id: str
    is_deleted: bool
    created_at: datetime
    updated_at: datetime
    user_info: Optional[UserInfo] = Field(None, description="用户信息")
    reactions: Optional[dict] = Field(
        None, description="E27：emoji → userId[] 映射"
    )
    attachments: Optional[List[dict]] = Field(
        None, description="E69：评论附件薄摘要 [{id,file_name,file_size,file_type}]"
    )

    model_config = ConfigDict(from_attributes=True)

    @field_validator('comment_type', mode='before')
    @classmethod
    def convert_comment_type(cls, v: Any) -> str:
        """将枚举值转换为小写字符串"""
        if isinstance(v, CommentType):
            return v.value
        return str(v).lower() if v else "comment"


# ============================================================================
# Issue Relation Schemas
# ============================================================================

class IssueRelationBase(BaseModel):
    """Issue 关系基础 Schema"""
    target_id: str = Field(..., description="目标 Issue ID")
    relation_type: RelationType = Field(..., description="关系类型")


class IssueRelationCreate(IssueRelationBase):
    """创建关系 Schema"""
    source_id: str = Field(..., description="源 Issue ID")


class IssueRelationResponse(IssueRelationBase):
    """关系响应 Schema"""
    id: int
    source_id: str
    created_at: datetime
    created_by: Optional[str]

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# Issue Timeline Schemas
# ============================================================================

class IssueTimelineResponse(BaseModel):
    """时间线响应 Schema"""
    id: str
    issue_id: str
    user_id: Optional[str]
    action_type: TimelineAction
    action_data: Optional[dict]
    created_at: datetime
    user_info: Optional[UserInfo] = Field(None, description="用户信息")

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# Query Params Schemas
# ============================================================================

class IssueQueryParams(BaseModel):
    """Issue 查询参数"""
    page: int = Field(1, ge=1, description="页码")
    page_size: int = Field(20, ge=1, le=100, description="每页数量")
    type: Optional[IssueType] = Field(None, description="类型筛选")
    status: Optional[IssueStatus] = Field(None, description="状态筛选")
    priority: Optional[IssuePriority] = Field(None, description="优先级筛选")
    project_id: Optional[str] = Field(None, description="项目 ID")
    assignee_id: Optional[str] = Field(None, description="负责人 ID")
    assignee_any: Optional[str] = Field(
        None, description="E71: match primary OR any collaborator"
    )
    reporter_id: Optional[str] = Field(None, description="报告人 ID")
    search: Optional[str] = Field(None, description="搜索关键词")
    cycle_id: Optional[str] = Field(
        None,
        description="Cycle ID 筛选；传 __none__ 表示无 Cycle",
    )
    milestone_id: Optional[str] = Field(
        None,
        description="Milestone ID 筛选；传 __none__ 表示无里程碑",
    )
    watching: Optional[bool] = Field(
        None,
        description="E19：仅当前用户关注的 Issue（需配合 user_id）",
    )
    due_before: Optional[str] = Field(
        None,
        description="E19：due_date 日期 ≤ YYYY-MM-DD",
    )
    start_before: Optional[str] = Field(
        None,
        description="E73：start_date 日期 ≤ YYYY-MM-DD",
    )
    start_after: Optional[str] = Field(
        None,
        description="E73：start_date 日期 ≥ YYYY-MM-DD",
    )
    due_soon: Optional[bool] = Field(
        None,
        description="E19：今日起 3 日内到期且未关闭",
    )
    sort_by: str = Field("created_at", description="排序字段")
    sort_order: str = Field("desc", pattern="^(asc|desc)$", description="排序方向")


# ============================================================================
# Bulk Operation Schemas
# ============================================================================

class IssueBoardMoveItem(BaseModel):
    """看板列内重排单项"""
    issue_id: str = Field(..., description="Issue ID")
    position: int = Field(..., ge=0, description="目标排序位置（0-based）")


class IssueBoardMove(BaseModel):
    """看板拖拽落盘：原子更新 status + position，可选同列重排"""
    issue_id: str = Field(..., description="被拖动的 Issue ID")
    status: IssueStatus = Field(..., description="目标状态列")
    position: int = Field(..., ge=0, description="目标列内位置（0-based）")
    ordered_ids: Optional[List[str]] = Field(
        None,
        description="目标列完整有序 ID 列表（含被拖动项）；若提供则按序重写各 position",
    )


class IssueBulkUpdate(BaseModel):
    """批量更新 Schema（E20：+cycle_id / tag_ids；需 X-Workspace-Id）"""
    issue_ids: List[str] = Field(..., min_length=1, description="Issue ID 列表")
    status: Optional[IssueStatus] = None
    priority: Optional[IssuePriority] = None
    assignee_id: Optional[str] = None
    cycle_id: Optional[str] = Field(
        None, description="目标 Cycle ID；显式 null 可清空（需出现在 payload）"
    )
    tag_ids: Optional[List[int]] = Field(
        None, description="替换为这些标签 ID；省略则不改标签；[] 清空"
    )


class IssueBulkDelete(BaseModel):
    """批量删除 Schema"""
    issue_ids: List[str] = Field(..., min_length=1, description="Issue ID 列表")


# ============================================================================
# Statistics Schemas
# ============================================================================

class IssueStatistics(BaseModel):
    """Issue 统计信息"""
    total: int = Field(..., description="总数")
    by_status: dict[str, int] = Field(..., description="按状态统计")
    by_priority: dict[str, int] = Field(..., description="按优先级统计")
    by_type: dict[str, int] = Field(..., description="按类型统计")
    open_count: int = Field(..., description="待处理数量")
    in_progress_count: int = Field(..., description="进行中数量")
    resolved_count: int = Field(..., description="已解决数量")
    closed_count: int = Field(..., description="已关闭数量")


# ============================================================================
# Issue Reaction Schemas
# ============================================================================

class IssueReactionBase(BaseModel):
    """反应基础 Schema"""
    emoji: str = Field(..., max_length=10, description="表情符号")


class IssueReactionCreate(IssueReactionBase):
    """创建反应 Schema"""
    pass


class IssueReactionResponse(IssueReactionBase):
    """反应响应 Schema"""
    id: int
    issue_id: str
    user_id: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class IssueReactionStats(BaseModel):
    """反应统计 Schema"""
    emoji: str = Field(..., description="表情符号")
    count: int = Field(..., description="反应数量")
    users: List[str] = Field(..., description="反应用户列表")
