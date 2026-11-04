"""标签相关 Schema（E7-S1）"""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class TagBase(BaseModel):
    name: str = Field(..., description="标签名称", max_length=100)
    color: str = Field("#3b82f6", description="标签颜色（十六进制）", max_length=20)
    group_id: Optional[str] = Field(None, description="标签组 ID")


class TagCreate(TagBase):
    pass


class TagUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=100)
    color: Optional[str] = Field(None, max_length=20)
    group_id: Optional[str] = Field(None, max_length=36)
    clear_group: bool = False


class TagResponse(BaseModel):
    id: int
    workspace_id: str
    name: str
    color: str
    group_id: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class TagBrief(BaseModel):
    id: int
    name: str
    color: str
    group_id: Optional[str] = None

    class Config:
        from_attributes = True


class TagListResponse(BaseModel):
    rows: list[TagResponse]
    total: int
