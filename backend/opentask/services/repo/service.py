"""仓库服务层"""
import logging
import os
import subprocess
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import HTTPException
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from opentask.models.repo.model import Repository, RepositoryBranch
from opentask.models.repo.schema import (
    RepositoryCreate,
    RepositoryUpdate,
    RepositoryBranchCreate,
    GitOperationResponse,
    GitStatusResponse,
    GitPRRequest,
)
from opentask.models.repo.enums import RepoStatus, GitProvider

logger = logging.getLogger(__name__)


class RepositoryService:
    """仓库服务"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, dto: RepositoryCreate) -> Repository:
        """
        创建仓库配置

        Args:
            dto: 创建仓库 DTO

        Returns:
            创建的仓库
        """
        # 验证项目是否存在（简单验证，假设项目表存在）
        # 这里可以添加项目存在性验证

        repository = Repository(
            id=str(uuid.uuid4()),
            name=dto.name,
            url=dto.url,
            branch=dto.branch,
            provider=dto.provider,
            is_active=dto.is_active,
            project_id=dto.project_id,
            requirement_id=dto.requirement_id,
            status=RepoStatus.IDLE,
        )
        self.db.add(repository)
        await self.db.commit()
        await self.db.refresh(repository)

        logger.info(f"Created repository: {repository.id} - {repository.name}")
        return repository

    async def get_list(
        self,
        project_id: Optional[str] = None,
        requirement_id: Optional[str] = None,
        is_active: Optional[bool] = None,
        provider: Optional[GitProvider] = None,
        page: int = 1,
        page_size: int = 50,
    ) -> dict:
        """
        获取仓库列表

        Args:
            project_id: 项目 ID 过滤
            requirement_id: 需求 ID 过滤
            is_active: 是否激活
            provider: Git 提供商
            page: 页码
            page_size: 每页数量

        Returns:
            仓库列表
        """
        query = select(Repository)

        # 应用过滤条件
        conditions = []
        if project_id:
            conditions.append(Repository.project_id == project_id)
        if requirement_id:
            conditions.append(Repository.requirement_id == requirement_id)
        if is_active is not None:
            conditions.append(Repository.is_active == is_active)
        if provider:
            conditions.append(Repository.provider == provider)

        if conditions:
            query = query.where(*conditions)

        # 获取总数
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self.db.execute(count_query)
        total = total_result.scalar_one()

        # 分页
        query = query.order_by(Repository.created_at.desc())
        query = query.offset((page - 1) * page_size).limit(page_size)

        result = await self.db.execute(query)
        repositories = list(result.scalars().all())

        return {
            "rows": [self.to_response(r) for r in repositories],
            "total": total,
            "current": page,
            "pageSize": page_size,
            "totalPages": (total + page_size - 1) // page_size,
        }

    async def get_by_id(self, repository_id: str) -> Repository:
        """
        获取单个仓库

        Args:
            repository_id: 仓库 ID

        Returns:
            仓库

        Raises:
            ValueError: 仓库不存在
        """
        result = await self.db.execute(
            select(Repository).where(Repository.id == repository_id)
        )
        repository = result.scalar_one_or_none()

        if not repository:
            raise ValueError(f"Repository {repository_id} not found")

        return repository

    async def update(self, repository_id: str, dto: RepositoryUpdate) -> Repository:
        """
        更新仓库配置

        Args:
            repository_id: 仓库 ID
            dto: 更新 DTO

        Returns:
            更新后的仓库

        Raises:
            ValueError: 仓库不存在
        """
        repository = await self.get_by_id(repository_id)

        # 更新字段
        update_data = dto.model_dump(exclude_unset=True, exclude={"status"})
        for field, value in update_data.items():
            setattr(repository, field, value)

        repository.updated_at = datetime.utcnow()

        await self.db.commit()
        await self.db.refresh(repository)

        logger.info(f"Updated repository: {repository_id}")
        return repository

    async def delete(self, repository_id: str) -> None:
        """
        删除仓库配置

        Args:
            repository_id: 仓库 ID
        """
        repository = await self.get_by_id(repository_id)
        await self.db.delete(repository)
        await self.db.commit()

        logger.info(f"Deleted repository: {repository_id}")

    # ============= 分支管理 =============

    async def get_branches(self, repository_id: str) -> list[RepositoryBranch]:
        """获取仓库的所有分支"""
        await self.get_by_id(repository_id)  # 确保仓库存在

        result = await self.db.execute(
            select(RepositoryBranch)
            .where(RepositoryBranch.repository_id == repository_id)
            .order_by(RepositoryBranch.is_default.desc(), RepositoryBranch.name.asc())
        )
        return list(result.scalars().all())

    async def create_branch(
        self, repository_id: str, dto: RepositoryBranchCreate
    ) -> RepositoryBranch:
        """创建分支记录"""
        await self.get_by_id(repository_id)  # 确保仓库存在

        branch = RepositoryBranch(
            repository_id=repository_id,
            name=dto.name,
            is_default=dto.is_default,
        )
        self.db.add(branch)
        await self.db.commit()
        await self.db.refresh(branch)

        return branch

    # ============= Git 操作 =============

    async def git_clone(
        self, repository_id: str, branch: Optional[str] = None
    ) -> GitOperationResponse:
        """
        克隆仓库

        Args:
            repository_id: 仓库 ID
            branch: 要克隆的分支（可选）

        Returns:
            操作结果
        """
        repository = await self.get_by_id(repository_id)

        # 更新状态为克隆中
        repository.status = RepoStatus.CLONING
        await self.db.commit()

        try:
            # 确定克隆路径
            clone_path = self._get_clone_path(repository)
            os.makedirs(clone_path, exist_ok=True)

            # 构建 git clone 命令
            clone_branch = branch or repository.branch
            url = repository.url

            cmd = ["git", "clone", "--branch", clone_branch, "--single-branch", url, clone_path]

            # 执行克隆
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300,  # 5 分钟超时
            )

            if result.returncode != 0:
                raise Exception(f"Git clone failed: {result.stderr}")

            # 更新仓库信息
            repository.local_path = clone_path
            repository.last_clone_at = datetime.utcnow()
            repository.status = RepoStatus.IDLE
            repository.error_message = None

            # 获取最新提交信息
            await self._update_last_commit(repository, clone_path)

            await self.db.commit()

            return GitOperationResponse(
                success=True,
                message="仓库克隆成功",
                details={"path": clone_path, "branch": clone_branch},
            )

        except Exception as e:
            repository.status = RepoStatus.ERROR
            repository.error_message = str(e)
            await self.db.commit()

            logger.exception(f"Clone repository failed: {repository_id}")
            return GitOperationResponse(success=False, message=str(e))

    async def git_pull(self, repository_id: str) -> GitOperationResponse:
        """拉取仓库最新代码"""
        repository = await self.get_by_id(repository_id)

        if not repository.local_path:
            return GitOperationResponse(success=False, message="仓库未克隆，请先执行克隆操作")

        try:
            cmd = ["git", "pull", "origin", repository.branch]
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=repository.local_path,
                timeout=60,
            )

            if result.returncode != 0:
                raise Exception(f"Git pull failed: {result.stderr}")

            repository.last_pull_at = datetime.utcnow()
            await self._update_last_commit(repository, repository.local_path)
            await self.db.commit()

            return GitOperationResponse(
                success=True, message="代码拉取成功", details={"branch": repository.branch}
            )

        except Exception as e:
            repository.status = RepoStatus.ERROR
            repository.error_message = str(e)
            await self.db.commit()

            logger.exception(f"Pull repository failed: {repository_id}")
            return GitOperationResponse(success=False, message=str(e))

    async def git_commit(
        self, repository_id: str, message: str, files: Optional[list[str]] = None
    ) -> GitOperationResponse:
        """提交代码更改"""
        repository = await self.get_by_id(repository_id)

        if not repository.local_path:
            return GitOperationResponse(success=False, message="仓库未克隆")

        try:
            # 添加文件
            if files:
                for file in files:
                    subprocess.run(
                        ["git", "add", file],
                        capture_output=True,
                        cwd=repository.local_path,
                        check=True,
                    )
            else:
                subprocess.run(
                    ["git", "add", "."],
                    capture_output=True,
                    cwd=repository.local_path,
                    check=True,
                )

            # 提交
            subprocess.run(
                ["git", "commit", "-m", message],
                capture_output=True,
                cwd=repository.local_path,
                check=True,
            )

            await self._update_last_commit(repository, repository.local_path)
            await self.db.commit()

            return GitOperationResponse(success=True, message="代码提交成功")

        except subprocess.CalledProcessError as e:
            return GitOperationResponse(
                success=False, message=f"提交失败: {e.stderr.decode() if e.stderr else str(e)}"
            )
        except Exception as e:
            logger.exception(f"Commit failed: {repository_id}")
            return GitOperationResponse(success=False, message=str(e))

    async def git_push(
        self, repository_id: str, branch: Optional[str] = None, force: bool = False
    ) -> GitOperationResponse:
        """推送代码到远程"""
        repository = await self.get_by_id(repository_id)

        if not repository.local_path:
            return GitOperationResponse(success=False, message="仓库未克隆")

        try:
            push_branch = branch or repository.branch
            cmd = ["git", "push", "origin", push_branch]
            if force:
                cmd.append("--force")

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=repository.local_path,
                timeout=60,
            )

            if result.returncode != 0:
                raise Exception(f"Git push failed: {result.stderr}")

            return GitOperationResponse(
                success=True, message="代码推送成功", details={"branch": push_branch}
            )

        except Exception as e:
            logger.exception(f"Push failed: {repository_id}")
            return GitOperationResponse(success=False, message=str(e))

    async def git_status(self, repository_id: str) -> GitStatusResponse:
        """获取仓库状态"""
        repository = await self.get_by_id(repository_id)

        if not repository.local_path:
            raise ValueError("仓库未克隆")

        try:
            # 获取当前分支
            branch_result = subprocess.run(
                ["git", "branch", "--show-current"],
                capture_output=True,
                text=True,
                cwd=repository.local_path,
                check=True,
            )
            current_branch = branch_result.stdout.strip()

            # 获取最新提交
            log_result = subprocess.run(
                ["git", "log", "-1", '--pretty=format:"%H|%an|%s"'],
                capture_output=True,
                text=True,
                cwd=repository.local_path,
                check=True,
            )
            commit_info = log_result.stdout.strip().strip('"').split("|")
            commit_hash = commit_info[0] if len(commit_info) > 0 else ""
            commit_author = commit_info[1] if len(commit_info) > 1 else ""
            commit_message = commit_info[2] if len(commit_info) > 2 else ""

            # 获取修改的文件
            status_result = subprocess.run(
                ["git", "status", "--porcelain"],
                capture_output=True,
                text=True,
                cwd=repository.local_path,
                check=True,
            )

            modified_files = []
            untracked_files = []

            for line in status_result.stdout.splitlines():
                if line:
                    status_code = line[:2]
                    file_path = line[3:]
                    if status_code.strip() == "??":
                        untracked_files.append(file_path)
                    else:
                        modified_files.append(file_path)

            return GitStatusResponse(
                branch=current_branch,
                commit=commit_hash,
                author=commit_author,
                message=commit_message,
                modified_files=modified_files,
                untracked_files=untracked_files,
                is_dirty=len(modified_files) > 0 or len(untracked_files) > 0,
            )

        except subprocess.CalledProcessError as e:
            logger.exception(f"Get git status failed: {repository_id}")
            raise Exception(f"获取仓库状态失败: {str(e)}")

    async def git_create_pr(
        self, repository_id: str, dto: GitPRRequest
    ) -> GitOperationResponse:
        """
        创建 Pull Request

        注意：这是一个占位实现，实际创建 PR 需要调用各平台的 API
        """
        repository = await self.get_by_id(repository_id)

        # TODO: 根据不同的 provider 调用对应的 API 创建 PR
        # - GitHub: 使用 GitHub API
        # - GitLab: 使用 GitLab API
        # - Gitea: 使用 Gitea API

        return GitOperationResponse(
            success=False,
            message=f"创建 PR 功能暂未实现，Provider: {repository.provider}",
            details={
                "provider": repository.provider,
                "source_branch": dto.source_branch,
                "target_branch": dto.target_branch,
            },
        )

    # ============= 辅助方法 =============

    def _get_clone_path(self, repository: Repository) -> str:
        """获取仓库克隆路径"""
        # 基于项目 ID 和仓库 ID 生成路径
        # 可以根据需要调整路径结构
        base_path = os.path.expanduser("~/opentask-repos")
        project_path = os.path.join(base_path, repository.project_id)
        return os.path.join(project_path, repository.id)

    async def _update_last_commit(self, repository: Repository, repo_path: str) -> None:
        """更新仓库的最新提交信息"""
        try:
            result = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                capture_output=True,
                text=True,
                cwd=repo_path,
                check=True,
            )
            repository.last_commit = result.stdout.strip()
        except Exception as e:
            logger.warning(f"Failed to get last commit: {e}")

    def to_response(self, repository: Repository) -> dict:
        """转换为响应格式"""
        return {
            "id": repository.id,
            "name": repository.name,
            "url": repository.url,
            "branch": repository.branch,
            "provider": repository.provider,
            "is_active": repository.is_active,
            "status": repository.status,
            "project_id": repository.project_id,
            "requirement_id": repository.requirement_id,
            "local_path": repository.local_path,
            "last_clone_at": repository.last_clone_at,
            "last_pull_at": repository.last_pull_at,
            "last_commit": repository.last_commit,
            "error_message": repository.error_message,
            "created_at": repository.created_at,
            "updated_at": repository.updated_at,
        }

    def to_branch_response(self, branch: RepositoryBranch) -> dict:
        """转换为分支响应格式"""
        return {
            "id": branch.id,
            "repository_id": branch.repository_id,
            "name": branch.name,
            "is_default": branch.is_default,
            "last_commit": branch.last_commit,
            "commit_message": branch.commit_message,
            "commit_author": branch.commit_author,
            "committed_at": branch.committed_at,
            "created_at": branch.created_at,
            "updated_at": branch.updated_at,
        }
