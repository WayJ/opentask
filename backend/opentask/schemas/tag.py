"""标签相关的 Schema 定义"""
# ============================================================================
# ⚠️ Tag 功能已移除 - 知识库不再需要 tag 功能
# 此文件已废弃，保留仅用于可能的数据库迁移回滚
# ============================================================================
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class TagBase(BaseModel):
    """标签基础 Schema"""
    name: str = Field(..., description="标签名称", max_length=50)
    color: str = Field("#3b82f6", description="标签颜色（十六进制）", max_length=20)


class TagCreate(TagBase):
    """创建标签 Schema"""
    pass


class TagUpdate(BaseModel):
    """更新标签 Schema"""
    name: Optional[str] = Field(None, max_length=50)
    color: Optional[str] = Field(None, max_length=20)


class TagResponse(TagBase):
    """标签响应 Schema"""
    id: int = Field(..., description="标签 ID")
    usage_count: int = Field(0, description="使用次数")
    created_at: datetime = Field(..., description="创建时间")

    class Config:
        from_attributes = True


class TagListResponse(BaseModel):
    """标签列表响应 Schema"""
    rows: list[TagResponse]
    total: int
