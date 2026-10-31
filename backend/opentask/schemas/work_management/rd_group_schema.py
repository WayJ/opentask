"""研发组相关 Schema"""
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime


class RdGroupMemberBase(BaseModel):
    """研发组成员基础 Schema"""
    user_id: str = Field(..., description="用户ID")
    role: str = Field(..., description="角色: director/leader/member")


class RdGroupMemberCreate(RdGroupMemberBase):
    """创建成员 Schema"""
    pass


class RdGroupMemberResponse(RdGroupMemberBase):
    """成员响应 Schema"""
    id: str
    group_id: str
    joined_at: datetime

    class Config:
        from_attributes = True


class RdGroupBase(BaseModel):
    """研发组基础 Schema"""
    name: str = Field(..., min_length=1, max_length=100, description="研发组名称")
    director_id: str = Field(..., description="产品总监ID")
    leader_id: str = Field(..., description="组长ID")


class RdGroupCreate(RdGroupBase):
    """创建研发组 Schema"""
    pass


class RdGroupUpdate(BaseModel):
    """更新研发组 Schema"""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    leader_id: Optional[str] = None
    status: Optional[str] = Field(None, pattern="^(active|inactive)$")


class RdGroupResponse(RdGroupBase):
    """研发组响应 Schema"""
    id: str
    status: str
    created_at: datetime
    updated_at: datetime
    members: List[RdGroupMemberResponse] = []

    class Config:
        from_attributes = True
