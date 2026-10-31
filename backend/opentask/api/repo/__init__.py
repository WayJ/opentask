"""Repository 模块 API 路由"""
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from opentask.models.repo.schema import (
    RepositoryCreate,
    RepositoryUpdate,
    RepositoryResponse,
    RepositoryBranchCreate,
    RepositoryBranchResponse,
    GitCloneRequest,
    GitCommitRequest,
    GitPushRequest,
    GitPRRequest,
    GitStatusResponse,
    GitOperationResponse,
)
from opentask.models.repo.enums import RepoStatus, GitProvider
from opentask.services.repo.service import RepositoryService
from opentask.repositories.base import get_session
from opentask.utils.response import success_response, error_response

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/repositories", tags=["Repositories"])


async def get_repository_service(
    db: AsyncSession = Depends(get_session)
) -> RepositoryService:
    """获取仓库服务依赖"""
    return RepositoryService(db)


@router.post("")
async def create_repository(
    dto: RepositoryCreate,
    service: RepositoryService = Depends(get_repository_service),
):
    """
    创建仓库配置

    - **name**: 仓库名称（必填）
    - **url**: 仓库 URL（必填）
    - **branch**: 默认分支（默认 main）
    - **provider**: Git 提供商
    - **project_id**: 项目 ID（必填）
    - **requirement_id**: 需求 ID（可选）
    """
    try:
        repository = await service.create(dto)
        return success_response(data=service.to_response(repository), message="仓库创建成功")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("")
async def list_repositories(
    project_id: Optional[str] = Query(None, description="按项目 ID 筛选"),
    requirement_id: Optional[str] = Query(None, description="按需求 ID 筛选"),
    is_active: Optional[bool] = Query(None, description="是否激活"),
    provider: Optional[GitProvider] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    service: RepositoryService = Depends(get_repository_service),
):
    """
    获取仓库列表

    支持按项目、需求、激活状态、提供商过滤和分页
    """
    result = await service.get_list(project_id, requirement_id, is_active, provider, page, page_size)
    return success_response(data=result)


@router.get("/{repository_id}")
async def get_repository(
    repository_id: str,
    service: RepositoryService = Depends(get_repository_service),
):
    """获取仓库详情"""
    try:
        repository = await service.get_by_id(repository_id)
        return success_response(data=service.to_response(repository))
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.put("/{repository_id}")
async def update_repository(
    repository_id: str,
    dto: RepositoryUpdate,
    service: RepositoryService = Depends(get_repository_service),
):
    """
    更新仓库配置

    支持更新名称、URL、分支、提供商、激活状态等
    """
    try:
        repository = await service.update(repository_id, dto)
        return success_response(data=service.to_response(repository), message="仓库更新成功")
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.delete("/{repository_id}")
async def delete_repository(
    repository_id: str,
    service: RepositoryService = Depends(get_repository_service),
):
    """
    删除仓库配置

    级联删除所有关联的分支等
    """
    try:
        await service.delete(repository_id)
        return success_response(message="仓库删除成功")
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# ============= 分支管理 =============

@router.get("/{repository_id}/branches")
async def list_branches(
    repository_id: str,
    service: RepositoryService = Depends(get_repository_service),
):
    """获取仓库的所有分支"""
    try:
        branches = await service.get_branches(repository_id)
        return success_response(data=[service.to_branch_response(b) for b in branches])
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/{repository_id}/branches")
async def create_branch(
    repository_id: str,
    dto: RepositoryBranchCreate,
    service: RepositoryService = Depends(get_repository_service),
):
    """
    创建分支记录

    - **name**: 分支名称（必填）
    - **is_default**: 是否为默认分支
    """
    try:
        branch = await service.create_branch(repository_id, dto)
        return success_response(data=service.to_branch_response(branch), message="分支创建成功")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ============= Git 操作 =============

@router.post("/{repository_id}/git/clone")
async def clone_repository(
    repository_id: str,
    dto: GitCloneRequest,
    service: RepositoryService = Depends(get_repository_service),
):
    """
    克隆仓库

    - **branch**: 要克隆的分支（可选，默认使用仓库默认分支）
    """
    try:
        result = await service.git_clone(repository_id, dto.branch)
        return success_response(data=result, message="仓库克隆成功")
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.exception("克隆仓库失败")
        return error_response(message=f"克隆失败: {str(e)}", data=GitOperationResponse(
            success=False,
            message=str(e)
        ))


@router.post("/{repository_id}/git/pull")
async def pull_repository(
    repository_id: str,
    service: RepositoryService = Depends(get_repository_service),
):
    """拉取仓库最新代码"""
    try:
        result = await service.git_pull(repository_id)
        return success_response(data=result, message="代码拉取成功")
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.exception("拉取代码失败")
        return error_response(message=f"拉取失败: {str(e)}", data=GitOperationResponse(
            success=False,
            message=str(e)
        ))


@router.post("/{repository_id}/git/commit")
async def commit_changes(
    repository_id: str,
    dto: GitCommitRequest,
    service: RepositoryService = Depends(get_repository_service),
):
    """
    提交代码更改

    - **message**: 提交消息（必填）
    - **files**: 要提交的文件列表（可选，默认提交所有）
    """
    try:
        result = await service.git_commit(repository_id, dto.message, dto.files)
        return success_response(data=result, message="代码提交成功")
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.exception("提交代码失败")
        return error_response(message=f"提交失败: {str(e)}", data=GitOperationResponse(
            success=False,
            message=str(e)
        ))


@router.post("/{repository_id}/git/push")
async def push_changes(
    repository_id: str,
    dto: GitPushRequest,
    service: RepositoryService = Depends(get_repository_service),
):
    """
    推送代码到远程

    - **branch**: 要推送的分支（可选，默认使用当前分支）
    - **force**: 是否强制推送
    """
    try:
        result = await service.git_push(repository_id, dto.branch, dto.force)
        return success_response(data=result, message="代码推送成功")
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.exception("推送代码失败")
        return error_response(message=f"推送失败: {str(e)}", data=GitOperationResponse(
            success=False,
            message=str(e)
        ))


@router.post("/{repository_id}/git/status")
async def get_git_status(
    repository_id: str,
    service: RepositoryService = Depends(get_repository_service),
):
    """获取仓库状态"""
    try:
        status = await service.git_status(repository_id)
        return success_response(data=status)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.exception("获取仓库状态失败")
        raise HTTPException(status_code=500, detail=f"获取状态失败: {str(e)}")


@router.post("/{repository_id}/git/pr")
async def create_pull_request(
    repository_id: str,
    dto: GitPRRequest,
    service: RepositoryService = Depends(get_repository_service),
):
    """
    创建 Pull Request

    - **title**: PR 标题（必填）
    - **description**: PR 描述
    - **source_branch**: 源分支（必填）
    - **target_branch**: 目标分支（默认 main）
    """
    try:
        result = await service.git_create_pr(repository_id, dto)
        return success_response(data=result, message="PR 创建成功")
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.exception("创建 PR 失败")
        return error_response(message=f"创建 PR 失败: {str(e)}", data=GitOperationResponse(
            success=False,
            message=str(e)
        ))
