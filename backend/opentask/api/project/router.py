"""项目和仓库管理 API 路由"""
import logging
from datetime import datetime
from typing import Any

from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException, Query, status, Body
from sqlalchemy.ext.asyncio import AsyncSession

from opentask.models.requirement.schema import (
    ProjectCreate,
    ProjectResponse,
    RepoConfigCreate,
    RepoConfigResponse,
    RequirementRepoCreate,
    RequirementRepoResponse,
)
from opentask.models.requirement.enums import MergeStatus
from opentask.services.project_service import ProjectService, RepoConfigService, RequirementRepoService
from opentask.services.milestone.service import MilestoneService, require_writer, serialize_milestone
from opentask.models.workspace.model import Workspace, WorkspaceMember
from opentask.services.user_center.rbac_service import RbacService
from opentask.repositories.base import get_session
from opentask.auth import authenticate
from opentask.models.user.model import UserModel
from opentask.utils.response import success_response, error_response, StatusCode
from opentask.api.workspace.deps import get_optional_workspace_context, require_workspace_context
from opentask.services.workspace.service import WorkspaceService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/projects", tags=["Projects"])

# 子路由器
repo_router = APIRouter(prefix="/{project_id}/repos", tags=["Repo Configs"])
requirement_repo_router = APIRouter(prefix="/requirement-repos", tags=["Requirement Repos"])


async def get_project_service(db: AsyncSession = Depends(get_session)) -> ProjectService:
    """获取项目服务依赖"""
    return ProjectService(db)


async def get_repo_service(db: AsyncSession = Depends(get_session)) -> RepoConfigService:
    """获取仓库配置服务依赖"""
    return RepoConfigService(db)


async def get_requirement_repo_service(db: AsyncSession = Depends(get_session)) -> RequirementRepoService:
    """获取需求-仓库关联服务依赖"""
    return RequirementRepoService(db)


# ============================================================================
# 项目路由
# ============================================================================

@router.post("")
async def create_project(
    dto: ProjectCreate,
    service: ProjectService = Depends(get_project_service),
    current_user: UserModel = Depends(authenticate),
    ws_ctx=Depends(get_optional_workspace_context),
):
    """创建项目（可选 X-Workspace-Id：写入 workspace_id）"""
    workspace, _member, user = ws_ctx
    # 部门归属快照：取创建人主部门写入（无归属则保持 NULL）
    dept_id = await RbacService(service.db).get_primary_dept_id(user)
    project = await service.create(
        dto,
        dept_id=dept_id,
        workspace_id=workspace.id if workspace else None,
    )
    return success_response(data=service.to_response(project), message="项目创建成功")


@router.get("")
async def list_projects(
    active_only: bool = Query(True, description="仅返回活跃项目"),
    service: ProjectService = Depends(get_project_service),
    current_user: UserModel = Depends(authenticate),
    ws_ctx=Depends(get_optional_workspace_context),
):
    """获取项目列表（部门数据范围 + 工作区隔离）"""
    workspace, _member, user = ws_ctx
    allowed = None
    ws_id = None
    if workspace is not None:
        # 显式工作区上下文：以租户成员资格为边界，不再叠加部门 SELF 空集过滤
        ws_id = workspace.id
        visible_dept_ids = None
    else:
        allowed = await WorkspaceService(service.db).member_workspace_ids(str(user.id))
        visible_dept_ids = await RbacService(service.db).get_visible_dept_ids(user)
    projects = await service.list_all(
        active_only,
        visible_dept_ids=visible_dept_ids,
        workspace_id=ws_id,
        allowed_workspace_ids=allowed,
    )
    return success_response(data=[service.to_response(p) for p in projects])


@router.get("/{project_id}")
async def get_project(
    project_id: str,
    service: ProjectService = Depends(get_project_service),
):
    """获取单个项目"""
    project = await service.get_by_id(project_id)
    return success_response(data=service.to_response(project))


class ProjectUpdateBody(BaseModel):
    """项目更新请求体（全部可选）"""
    name: str | None = None
    description: str | None = None
    starts_at: datetime | None = None
    target_date: datetime | None = None


@router.put("/{project_id}")
async def update_project(
    project_id: str,
    body: ProjectUpdateBody = Body(...),
    service: ProjectService = Depends(get_project_service),
):
    """更新项目（含 starts_at / target_date）"""
    kwargs = {}
    if "name" in body.model_fields_set:
        kwargs["name"] = body.name
    if "description" in body.model_fields_set:
        kwargs["description"] = body.description
    if "starts_at" in body.model_fields_set:
        kwargs["starts_at"] = body.starts_at
    if "target_date" in body.model_fields_set:
        kwargs["target_date"] = body.target_date
    project = await service.update(project_id, **kwargs)
    return success_response(data=service.to_response(project), message="项目更新成功")


@router.delete("/{project_id}")
async def delete_project(
    project_id: str,
    service: ProjectService = Depends(get_project_service),
):
    """删除项目"""
    await service.delete(project_id)
    return success_response(message="项目删除成功")


# ============================================================================
# 仓库配置路由
# ============================================================================

@repo_router.post("")
async def create_repo_config(
    project_id: str,
    dto: RepoConfigCreate,
    service: RepoConfigService = Depends(get_repo_service),
):
    """创建仓库配置"""
    dto.project_id = project_id
    repo = await service.create(dto)
    return success_response(data=service.to_response(repo), message="仓库配置创建成功")


@repo_router.get("")
async def list_repo_configs(
    project_id: str,
    service: RepoConfigService = Depends(get_repo_service),
):
    """获取项目的所有仓库配置"""
    repos = await service.list_by_project(project_id)
    return success_response(data=[service.to_response(r) for r in repos])


@repo_router.get("/{repo_id}")
async def get_repo_config(
    repo_id: int,
    service: RepoConfigService = Depends(get_repo_service),
):
    """获取单个仓库配置"""
    repo = await service.get_by_id(repo_id)
    return success_response(data=service.to_response(repo))


class RepoConfigUpdateBody(BaseModel):
    """仓库配置更新请求体（全部可选，仅更新提供字段）

    前端 project.ts 的 updateRepoConfig 以 JSON body 提交（PUT data），
    原先的裸参数签名会被 FastAPI 解析成 query 参数，body 永远读不到。
    """
    name: str | None = None
    url: str | None = None
    main_branch: str | None = None


@repo_router.put("/{repo_id}")
async def update_repo_config(
    repo_id: int,
    dto: RepoConfigUpdateBody,
    service: RepoConfigService = Depends(get_repo_service),
):
    """更新仓库配置"""
    repo = await service.update(
        repo_id,
        name=dto.name,
        url=dto.url,
        main_branch=dto.main_branch,
    )
    return success_response(data=service.to_response(repo), message="仓库配置更新成功")


@repo_router.delete("/{repo_id}")
async def delete_repo_config(
    repo_id: int,
    service: RepoConfigService = Depends(get_repo_service),
):
    """删除仓库配置"""
    await service.delete(repo_id)
    return success_response(message="仓库配置删除成功")


# ============================================================================
# 需求-仓库关联路由
# ============================================================================

@requirement_repo_router.post("")
async def link_requirement_repo(
    dto: RequirementRepoCreate,
    service: RequirementRepoService = Depends(get_requirement_repo_service),
):
    """关联需求和仓库"""
    association = await service.create(dto)
    return success_response(data=service.to_response(association), message="关联成功")


@requirement_repo_router.get("/{requirement_id}")
async def get_requirement_repos(
    requirement_id: str,
    service: RequirementRepoService = Depends(get_requirement_repo_service),
):
    """获取需求的所有仓库"""
    associations = await service.get_by_requirement(requirement_id)
    return success_response(data=[service.to_response(a) for a in associations])


class RequirementRepoUpdateBody(BaseModel):
    """需求-仓库关联更新请求体（全部可选）

    与 update_repo_config 同理：裸参数会被解析为 query 参数，JSON body 读不到。
    """
    branch: str | None = None
    pr_url: str | None = None
    merge_status: MergeStatus | None = None


@requirement_repo_router.put("/{requirement_id}/repos/{repo_id}")
async def update_requirement_repo(
    requirement_id: str,
    repo_id: int,
    dto: RequirementRepoUpdateBody,
    service: RequirementRepoService = Depends(get_requirement_repo_service),
):
    """更新需求-仓库关联信息（分支、PR等）"""
    association = await service.update_branch(
        requirement_id,
        repo_id,
        branch=dto.branch,
        pr_url=dto.pr_url,
        merge_status=dto.merge_status,
    )
    return success_response(data=service.to_response(association), message="关联信息更新成功")


@requirement_repo_router.delete("/{requirement_id}/repos/{repo_id}")
async def unlink_requirement_repo(
    requirement_id: str,
    repo_id: int,
    service: RequirementRepoService = Depends(get_requirement_repo_service),
):
    """取消需求和仓库的关联"""
    await service.delete(requirement_id, repo_id)
    return success_response(message="关联已取消")



# ============================================================================
# 里程碑（E8-S1）
# ============================================================================

milestones_router = APIRouter(prefix="/{project_id}/milestones", tags=["Milestones"])


class MilestoneCreateBody(BaseModel):
    name: str
    description: str | None = None
    target_date: datetime | None = None
    status: str = "planned"
    position: int = 0


class MilestoneUpdateBody(BaseModel):
    name: str | None = None
    description: str | None = None
    target_date: datetime | None = None
    status: str | None = None
    position: int | None = None


@milestones_router.get("")
async def list_milestones(
    project_id: str,
    ctx: tuple[Workspace, WorkspaceMember, UserModel] = Depends(require_workspace_context),
    db: AsyncSession = Depends(get_session),
):
    ws, _member, _user = ctx
    rows = await MilestoneService(db).list(project_id=project_id, workspace_id=ws.id)
    return success_response(data=[serialize_milestone(r) for r in rows])


@milestones_router.post("")
async def create_milestone(
    project_id: str,
    body: MilestoneCreateBody,
    ctx: tuple[Workspace, WorkspaceMember, UserModel] = Depends(require_workspace_context),
    db: AsyncSession = Depends(get_session),
):
    ws, member, _user = ctx
    require_writer(member)
    row = await MilestoneService(db).create(
        project_id=project_id,
        workspace_id=ws.id,
        name=body.name,
        description=body.description,
        target_date=body.target_date,
        status=body.status,
        position=body.position,
    )
    return success_response(data=serialize_milestone(row), message="里程碑已创建")


@milestones_router.get("/{milestone_id}")
async def get_milestone(
    project_id: str,
    milestone_id: str,
    ctx: tuple[Workspace, WorkspaceMember, UserModel] = Depends(require_workspace_context),
    db: AsyncSession = Depends(get_session),
):
    ws, _member, _user = ctx
    row = await MilestoneService(db).get(
        milestone_id, project_id=project_id, workspace_id=ws.id
    )
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="里程碑不存在")
    return success_response(data=serialize_milestone(row))


@milestones_router.patch("/{milestone_id}")
async def update_milestone(
    project_id: str,
    milestone_id: str,
    body: MilestoneUpdateBody,
    ctx: tuple[Workspace, WorkspaceMember, UserModel] = Depends(require_workspace_context),
    db: AsyncSession = Depends(get_session),
):
    ws, member, _user = ctx
    require_writer(member)
    svc = MilestoneService(db)
    row = await svc.get(milestone_id, project_id=project_id, workspace_id=ws.id)
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="里程碑不存在")
    kwargs = {}
    if "name" in body.model_fields_set:
        kwargs["name"] = body.name
    if "description" in body.model_fields_set:
        kwargs["description"] = body.description
    if "target_date" in body.model_fields_set:
        kwargs["target_date"] = body.target_date
    if "status" in body.model_fields_set:
        kwargs["status"] = body.status
    if "position" in body.model_fields_set:
        kwargs["position"] = body.position
    row = await svc.update(row, **kwargs)
    return success_response(data=serialize_milestone(row), message="里程碑已更新")


@milestones_router.delete("/{milestone_id}")
async def delete_milestone(
    project_id: str,
    milestone_id: str,
    ctx: tuple[Workspace, WorkspaceMember, UserModel] = Depends(require_workspace_context),
    db: AsyncSession = Depends(get_session),
):
    ws, member, _user = ctx
    require_writer(member)
    svc = MilestoneService(db)
    row = await svc.get(milestone_id, project_id=project_id, workspace_id=ws.id)
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="里程碑不存在")
    await svc.delete(row)
    return success_response(message="里程碑已删除")


# 将子路由器添加到主路由器
router.include_router(repo_router)
router.include_router(milestones_router)
router.include_router(requirement_repo_router)
