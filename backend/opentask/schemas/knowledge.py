"""知识 Pydantic Schema"""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


class KnowledgeBase(BaseModel):
    """知识基础 Schema"""
    title: str = Field(..., description="知识标题")
    content: str = Field(..., description="知识内容")
    category_id: Optional[int] = Field(None, description="分类 ID")
    visibility: Optional[str] = Field("internal", description="可见性")


class KnowledgeCreate(KnowledgeBase):
    """创建知识 Schema"""
    knowledge_base_id: str = Field(..., description="知识库 ID")


class KnowledgeUpdate(BaseModel):
    """更新知识 Schema"""
    title: Optional[str] = None
    content: Optional[str] = None
    category_id: Optional[int] = None
    status: Optional[str] = None
    visibility: Optional[str] = None


class KnowledgeResponse(KnowledgeBase):
    """知识响应 Schema"""
    id: str
    knowledge_base_id: str
    knowledge_base_name: Optional[str] = None
    slug: str
    status: str
    visibility: str
    version: int
    view_count: int
    like_count: int
    created_by: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ============================================================================
# ⚠️ Tag 功能已移除 - 知识库不再需要 tag 功能
# class TagResponse(BaseModel):
#     """标签响应 Schema"""
#     id: int
#     name: str
#     color: str
#     usage_count: int
#
#     class Config:
#         from_attributes = True
# ============================================================================


class CategoryResponse(BaseModel):
    """分类响应 Schema"""
    id: int
    name: str
    icon: Optional[str] = None
    sort_order: int
    parent_id: Optional[int] = None

    class Config:
        from_attributes = True
