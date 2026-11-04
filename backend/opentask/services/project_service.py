"""项目和仓库管理服务"""
import logging
from typing import Any

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from opentask.models.requirement.model import Project, RepoConfig, RequirementRepo
from opentask.models.requirement.schema import (
    ProjectCreate,
    ProjectResponse,
    RepoConfigCreate,
    RepoConfigResponse,
    RequirementRepoCreate,
    RequirementRepoResponse,
)
from opentask.services.user_center.rbac_service import RbacService

logger = logging.getLogger(__name__)


class ProjectService:
    """项目管理服务"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(
        self,
        dto: ProjectCreate,
        dept_id: str | None = None,
        workspace_id: str | None = None,
    ) -> Project:
        """创建项目

        dept_id: 创建人主部门 id 快照（None 表示无归属，行保持 NULL）
        workspace_id: 所属工作区（E3-S1）
        """
        project = Project(
            name=dto.name,
            description=dto.description,
            dept_id=dept_id,  # 部门归属快照：创建时创建人的主部门
            workspace_id=workspace_id,
        )
        self.db.add(project)
        await self.db.commit()
        await self.db.refresh(project)
        logger.info(f"Created project: {project.id}")
        return project

    async def get_by_id(self, project_id: str) -> Project:
        """获取项目"""
        result = await self.db.execute(
            select(Project).where(Project.id == project_id)
        )
        project = result.scalar_one_or_none()
        if not project:
            raise HTTPException(status_code=404, detail=f"Project {project_id} not found")
        return project

    async def list_all(
        self,
        active_only: bool = True,
        visible_dept_ids: set[str] | None = None,
        workspace_id: str | None = None,
        allowed_workspace_ids: list[str] | None = None,
    ) -> list[Project]:
        """获取所有项目

        visible_dept_ids: 数据范围可见部门集（None=不过滤；项目表无 created_by，
        空集（SELF）时结果恒空——项目均为部门资产）
        workspace_id: 当前工作区（精确过滤）
        allowed_workspace_ids: 无精确工作区时，限制在成员工作区 ∪ NULL
        """
        from sqlalchemy import or_

        query = select(Project)
        if active_only:
            query = query.where(Project.is_active == True)
        if workspace_id is not None:
            query = query.where(Project.workspace_id == workspace_id)
        elif allowed_workspace_ids is not None:
            query = query.where(
                or_(
                    Project.workspace_id.in_(allowed_workspace_ids),
                    Project.workspace_id.is_(None),
                )
            )
        # 数据范围过滤（visible_dept_ids=None 时原样返回，旧调用零破坏）
        query = RbacService(session=None).apply_data_scope(
            query,
            visible_dept_ids,
            dept_col=Project.dept_id,
        )
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def update(
        self,
        project_id: str,
        name: str | None = None,
        description: str | None = None,
        starts_at=...,
        target_date=...,
    ) -> Project:
        """更新项目（含 E8-S1 starts_at / target_date）"""
        from datetime import datetime

        project = await self.get_by_id(project_id)
        logger.info(f"Before update - project: {project.id}, name={project.name}, description={project.description}, received name={name}, description={description}")

        def _parse(value):
            if value is None:
                return None
            if isinstance(value, datetime):
                return value.replace(tzinfo=None) if value.tzinfo else value
            if isinstance(value, str):
                text = value.strip().replace("Z", "+00:00")
                dt = datetime.fromisoformat(text)
                return dt.replace(tzinfo=None) if dt.tzinfo else dt
            return value

        updated = False
        if name is not None and name != "" and name != project.name:
            project.name = name
            updated = True
            logger.info(f"Updating name to: {name}")
        if description is not None and description != project.description:
            project.description = description
            updated = True
            logger.info(f"Updating description to: {description}")
        if starts_at is not ...:
            project.starts_at = _parse(starts_at)
            updated = True
        if target_date is not ...:
            project.target_date = _parse(target_date)
            updated = True

        if updated:
            await self.db.flush()
            await self.db.commit()
            await self.db.refresh(project)
            logger.info(f"After update - project: {project.id}, name={project.name}, description={project.description}")
        else:
            logger.info("No updates needed")

        return project

    async def delete(self, project_id: str) -> None:
        """删除项目"""
        project = await self.get_by_id(project_id)
        await self.db.delete(project)
        await self.db.commit()
        logger.info(f"Deleted project: {project_id}")

    def to_response(self, project: Project) -> ProjectResponse:
        """转换为响应 Schema"""
        return ProjectResponse(
            id=project.id,
            name=project.name,
            description=project.description,
            is_active=project.is_active,
            created_at=project.created_at,
            updated_at=project.updated_at,
            starts_at=getattr(project, "starts_at", None),
            target_date=getattr(project, "target_date", None),
        )


class RepoConfigService:
    """仓库配置服务"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, dto: RepoConfigCreate) -> RepoConfig:
        """创建仓库配置"""
        # 验证项目存在
        result = await self.db.execute(
            select(Project).where(Project.id == dto.project_id)
        )
        if not result.scalar_one_or_none():
            raise HTTPException(status_code=404, detail=f"Project {dto.project_id} not found")

        repo = RepoConfig(
            project_id=dto.project_id,
            name=dto.name,
            url=dto.url,
            main_branch=dto.main_branch,
        )
        self.db.add(repo)
        await self.db.commit()
        await self.db.refresh(repo)
        logger.info(f"Created repo config: {repo.id}")
        return repo

    async def get_by_id(self, repo_id: int) -> RepoConfig:
        """获取仓库配置"""
        result = await self.db.execute(
            select(RepoConfig).where(RepoConfig.id == repo_id)
        )
        repo = result.scalar_one_or_none()
        if not repo:
            raise HTTPException(status_code=404, detail=f"RepoConfig {repo_id} not found")
        return repo

    async def list_by_project(self, project_id: str) -> list[RepoConfig]:
        """获取项目的所有仓库"""
        result = await self.db.execute(
            select(RepoConfig).where(RepoConfig.project_id == project_id)
        )
        return list(result.scalars().all())

    async def update(self, repo_id: int, **kwargs) -> RepoConfig:
        """更新仓库配置"""
        repo = await self.get_by_id(repo_id)
        for key, value in kwargs.items():
            if value is not None and hasattr(repo, key):
                setattr(repo, key, value)
        await self.db.commit()
        await self.db.refresh(repo)
        return repo

    async def delete(self, repo_id: int) -> None:
        """删除仓库配置"""
        repo = await self.get_by_id(repo_id)
        await self.db.delete(repo)
        await self.db.commit()
        logger.info(f"Deleted repo config: {repo_id}")

    def to_response(self, repo: RepoConfig) -> RepoConfigResponse:
        """转换为响应 Schema"""
        return RepoConfigResponse(
            id=repo.id,
            project_id=repo.project_id,
            name=repo.name,
            url=repo.url,
            main_branch=repo.main_branch,
            created_at=repo.created_at,
            updated_at=repo.updated_at,
        )


class RequirementRepoService:
    """需求-仓库关联服务"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, dto: RequirementRepoCreate) -> RequirementRepo:
        """创建关联"""
        association = RequirementRepo(
            requirement_id=dto.requirement_id,
            repo_id=dto.repo_id,
        )
        self.db.add(association)
        await self.db.commit()
        await self.db.refresh(association)
        return association

    async def update_branch(
        self,
        requirement_id: str,
        repo_id: int,
        branch: str | None = None,
        pr_url: str | None = None,
        merge_status: str | None = None,
    ) -> RequirementRepo:
        """更新关联信息（分支、PR等）"""
        result = await self.db.execute(
            select(RequirementRepo).where(
                RequirementRepo.requirement_id == requirement_id,
                RequirementRepo.repo_id == repo_id,
            )
        )
        association = result.scalar_one_or_none()
        if not association:
            raise HTTPException(status_code=404, detail="Requirement-Repo association not found")

        if branch is not None:
            association.branch = branch
        if pr_url is not None:
            association.pr_url = pr_url
        if merge_status is not None:
            association.merge_status = merge_status

        await self.db.commit()
        await self.db.refresh(association)
        return association

    async def get_by_requirement(self, requirement_id: str) -> list[RequirementRepo]:
        """获取需求的所有仓库"""
        result = await self.db.execute(
            select(RequirementRepo).where(RequirementRepo.requirement_id == requirement_id)
        )
        return list(result.scalars().all())

    async def delete(self, requirement_id: str, repo_id: int) -> None:
        """删除关联"""
        result = await self.db.execute(
            select(RequirementRepo).where(
                RequirementRepo.requirement_id == requirement_id,
                RequirementRepo.repo_id == repo_id,
            )
        )
        association = result.scalar_one_or_none()
        if association:
            await self.db.delete(association)
            await self.db.commit()

    def to_response(self, association: RequirementRepo) -> RequirementRepoResponse:
        """转换为响应 Schema"""
        return RequirementRepoResponse(
            id=association.id,
            requirement_id=association.requirement_id,
            repo_id=association.repo_id,
            branch=association.branch,
            pr_url=association.pr_url,
            merge_status=association.merge_status,
            created_at=association.created_at,
            updated_at=association.updated_at,
        )
