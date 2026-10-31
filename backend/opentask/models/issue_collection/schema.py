"""Issue Collection 相关的 Pydantic Schemas"""
from datetime import datetime
from typing import Optional, List, Any
from pydantic import BaseModel, Field, ConfigDict, field_validator

from .enums import CollectionStatus
from opentask.models.issue.schema import UserInfo


# ============================================================================
# Issue Collection Schemas
# ============================================================================

class IssueCollectionBase(BaseModel):
    """问题集基础 Schema"""
    title: str = Field(..., min_length=1, max_length=255, description="问题集标题")
    description: Optional[str] = Field(None, description="问题描述（Markdown 格式）")
    status: CollectionStatus = Field(default=CollectionStatus.PENDING, description="状态")


class IssueCollectionCreate(IssueCollectionBase):
    """创建问题集 Schema"""
    pass


class IssueCollectionUpdate(BaseModel):
    """更新问题集 Schema"""
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    status: Optional[CollectionStatus] = None
    issue_ids: Optional[List[str]] = Field(None, description="关联的 Issue ID 列表")


class CollectionStatistics(BaseModel):
    """问题集统计信息"""
    total: int = Field(..., description="总问题数")
    completed: int = Field(..., description="已完成数")
    in_progress: int = Field(..., description="处理中数")
    pending: int = Field(..., description="待处理数")
    completion_rate: float = Field(..., description="完成率")


class IssueCollectionResponse(IssueCollectionBase):
    """问题集响应 Schema"""
    id: str
    issue_ids: List[str] = Field(default_factory=list, description="关联的 Issue ID 列表")
    creator_id: str
    created_at: datetime
    updated_at: datetime

    # 关联信息（需要在 API 层手动填充）
    creator: Optional[UserInfo] = Field(None, description="创建人信息")
    statistics: Optional[CollectionStatistics] = Field(None, description="统计信息")

    model_config = ConfigDict(from_attributes=True)

    @field_validator('creator', mode='before')
    @classmethod
    def convert_user_model_to_info(cls, v: Any) -> Optional[UserInfo]:
        """将 UserModel 转换为 UserInfo"""
        if v is None:
            return None
        if isinstance(v, UserInfo):
            return v
        if isinstance(v, dict):
            # 如果已经是字典，直接使用
            return v
        try:
            if hasattr(v, 'id'):
                user_id = str(v.id) if v.id else None
                user_name = getattr(v, 'name', None)
                jnpf_name = getattr(v, 'jnpf_name', None)
                jnpf_account = getattr(v, 'jnpf_account', None)
                if user_id:
                    return UserInfo(
                        id=user_id,
                        name=user_name,
                        jnpf_name=jnpf_name,
                        jnpf_account=jnpf_account
                    )
        except Exception:
            # 如果访问属性失败（如 SQLAlchemy 异步关系），返回 None
            pass
        return None


class IssueCollectionListResponse(BaseModel):
    """问题集列表响应 Schema"""
    total: int = Field(..., description="总数")
    items: List[IssueCollectionResponse] = Field(..., description="问题集列表")


# ============================================================================
# Parse Request/Response Schemas
# ============================================================================

class IssueParseRequest(BaseModel):
    """问题拆解请求 Schema"""
    issues: List[dict] = Field(..., description="拆解出的问题列表")


class IssueParseResponse(BaseModel):
    """问题拆解响应 Schema"""
    message: str = Field(..., description="响应消息")
    parsed_count: int = Field(..., description="成功拆解的问题数")
    issue_ids: List[str] = Field(..., description="创建的 Issue ID 列表")
