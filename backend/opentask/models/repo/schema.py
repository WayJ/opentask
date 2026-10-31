"""Repository Pydantic Schema"""
from datetime import datetime
from typing import Optional
from pydantic import Field, BaseModel

from .enums import RepoStatus, GitProvider


class RepositoryBase(BaseModel):
    """仓库基础 Schema"""
    name: str = Field(..., description="仓库名称", min_length=1, max_length=255)
    url: str = Field(..., description="仓库 URL", min_length=1, max_length=500)
    branch: str = Field("main", description="默认分支", max_length=255)
    provider: GitProvider = Field(GitProvider.CUSTOM, description="Git 提供商")
    is_active: bool = Field(True, description="是否激活")


class RepositoryCreate(RepositoryBase):
    """创建仓库 Schema"""
    project_id: str = Field(..., description="项目 ID")
    requirement_id: Optional[str] = Field(None, description="需求 ID (可选)")


class RepositoryUpdate(BaseModel):
    """更新仓库 Schema"""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    url: Optional[str] = Field(None, min_length=1, max_length=500)
    branch: Optional[str] = Field(None, max_length=255)
    provider: Optional[GitProvider] = None
    is_active: Optional[bool] = None
    status: Optional[RepoStatus] = None
    local_path: Optional[str] = None
    auth_token: Optional[str] = Field(None, max_length=500)


class RepositoryResponse(RepositoryBase):
    """仓库响应 Schema"""
    id: str
    project_id: str
    requirement_id: Optional[str]
    local_path: Optional[str]
    status: RepoStatus
    last_clone_at: Optional[datetime]
    last_pull_at: Optional[datetime]
    last_commit: Optional[str]
    error_message: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class RepositoryBranchBase(BaseModel):
    """仓库分支基础 Schema"""
    name: str = Field(..., description="分支名称", min_length=1, max_length=255)
    is_default: bool = Field(False, description="是否为默认分支")


class RepositoryBranchCreate(RepositoryBranchBase):
    """创建分支 Schema"""
    repository_id: str = Field(..., description="仓库 ID")


class RepositoryBranchResponse(RepositoryBranchBase):
    """分支响应 Schema"""
    id: int
    repository_id: str
    last_commit: Optional[str]
    commit_message: Optional[str]
    commit_author: Optional[str]
    committed_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# Git 操作相关的 Schema
class GitCloneRequest(BaseModel):
    """克隆仓库请求 Schema"""
    branch: Optional[str] = Field(None, description="要克隆的分支 (可选，默认使用仓库默认分支)")


class GitCommitRequest(BaseModel):
    """提交请求 Schema"""
    message: str = Field(..., description="提交消息", min_length=1, max_length=2000)
    files: Optional[list[str]] = Field(None, description="要提交的文件列表 (可选，默认提交所有)")


class GitPushRequest(BaseModel):
    """推送请求 Schema"""
    branch: Optional[str] = Field(None, description="要推送的分支 (可选，默认使用当前分支)")
    force: bool = Field(False, description="是否强制推送")


class GitPRRequest(BaseModel):
    """创建 PR 请求 Schema"""
    title: str = Field(..., description="PR 标题", min_length=1, max_length=255)
    description: Optional[str] = Field(None, description="PR 描述")
    source_branch: str = Field(..., description="源分支", min_length=1, max_length=255)
    target_branch: str = Field("main", description="目标分支", min_length=1, max_length=255)


class GitStatusResponse(BaseModel):
    """Git 状态响应 Schema"""
    branch: str = Field(..., description="当前分支")
    commit: str = Field(..., description="当前提交 hash")
    author: str = Field(..., description="提交作者")
    message: str = Field(..., description="提交消息")
    modified_files: list[str] = Field(default_factory=list, description="修改的文件")
    untracked_files: list[str] = Field(default_factory=list, description="未跟踪的文件")
    is_dirty: bool = Field(False, description="是否有未提交的更改")


class GitOperationResponse(BaseModel):
    """Git 操作响应 Schema"""
    success: bool = Field(..., description="操作是否成功")
    message: str = Field(..., description="操作消息")
    details: Optional[dict] = Field(None, description="详细信息")
