"""知识库 Pydantic Schema"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class KnowledgeBaseBase(BaseModel):
    """知识库基础 Schema"""
    name: str = Field(..., description="知识库名称")
    description: Optional[str] = Field(None, description="知识库描述")
    icon: Optional[str] = Field(None, description="知识库图标 URL")
    repository_url: Optional[str] = Field(None, description="代码仓库地址")


class KnowledgeBaseCreate(KnowledgeBaseBase):
    """创建知识库 Schema"""
    pass


class KnowledgeBaseUpdate(BaseModel):
    """更新知识库 Schema"""
    name: Optional[str] = None
    description: Optional[str] = None
    icon: Optional[str] = None
    repository_url: Optional[str] = None
    status: Optional[str] = None


class KnowledgeBaseResponse(KnowledgeBaseBase):
    """知识库响应 Schema"""
    id: str
    status: str
    knowledge_count: int = 0
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ProjectAssociateRequest(BaseModel):
    """关联项目请求 Schema"""
    project_id: str = Field(..., description="项目 ID")
