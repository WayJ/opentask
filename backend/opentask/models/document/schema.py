"""文档模块 Pydantic Schema - 简化的附件模型

Document = Attachment，统一的概念
"""
from datetime import datetime
from typing import Any
from pydantic import BaseModel, Field

from opentask.models.document.enums import DocumentStatus


# ============================================================================
# 文档相关 Schema（Document = Attachment）
# ============================================================================


class DocumentBase(BaseModel):
    """文档基础 Schema"""
    status: DocumentStatus = Field(
        default=DocumentStatus.DRAFT, description="文档状态"
    )


class DocumentCreate(DocumentBase):
    """创建文档 Schema（独立 API，已废弃 - 现在使用文件上传）"""
    entity_type: str = Field(..., description="实体类型 (requirement/task/project/repo 等)")
    entity_id: str = Field(..., description="实体 ID")
    created_by: str | None = Field(None, description="创建者 ID")


class DocumentUpdate(BaseModel):
    """更新文档 Schema（仅用于 JSON 更新，文件更新使用 Form）"""
    status: DocumentStatus | None = Field(None, description="文档状态")
    updated_by: str | None = Field(None, description="更新者 ID")


class DocumentResponse(DocumentBase):
    """文档响应 Schema"""
    id: str
    entity_type: str
    entity_id: str
    file_name: str
    file_path: str
    file_type: str
    file_size: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ============================================================================
# 分页响应 Schema
# ============================================================================


class DocumentListResponse(BaseModel):
    """文档列表响应 Schema"""
    data: list[DocumentResponse]
    total: int
    page: int
    page_size: int
