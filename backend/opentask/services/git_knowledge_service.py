"""
Git 知识库服务

提供 Git 仓库代理功能，用于 Web 编辑器直接操作 Git 仓库
"""

import shutil
import logging
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime

from git import Repo
from sqlalchemy import select

from opentask.models.knowledge_base.model import KnowledgeBase
from opentask.repositories.base import get_session

logger = logging.getLogger(__name__)


class GitKnowledgeService:
    """Git 知识库服务

    提供以下功能：
    - 克隆和管理 Git 仓库缓存
    - 读取文件内容
    - 提交文件变更
    - 获取历史记录
    - 获取 diff
    - 创建分支
    """

    def __init__(self, cache_dir: str = "/tmp/knowledge_cache"):
        """
        初始化 Git 知识库服务

        Args:
            cache_dir: 本地缓存目录
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"GitKnowledgeService 初始化完成，缓存目录: {self.cache_dir}")

    def _get_repo_path(self, kb_id: str) -> Path:
        """获取知识库的本地缓存路径"""
        return self.cache_dir / kb_id

    async def _get_kb_info(self, kb_id: str) -> Optional[KnowledgeBase]:
        """获取知识库信息"""
        async with get_session() as db:
            result = await db.execute(
                select(KnowledgeBase).where(KnowledgeBase.id == kb_id)
            )
            return result.scalar_one_or_none()

    async def ensure_cloned(
        self,
        repo_url: str,
        kb_id: str,
        branch: str = "main"
    ) -> Path:
        """
        确保仓库已克隆到本地缓存

        Args:
            repo_url: Git 仓库 URL
            kb_id: 知识库 ID
            branch: 分支名称

        Returns:
            本地仓库路径
        """
        repo_path = self._get_repo_path(kb_id)

        try:
            if not repo_path.exists():
                logger.info(f"克隆仓库 {repo_url} -> {repo_path}")
                Repo.clone_from(
                    repo_url,
                    repo_path,
                    branch=branch
                )
                logger.info(f"仓库克隆成功: {kb_id}")
            else:
                # 拉取最新代码
                logger.info(f"拉取最新代码 {kb_id}")
                repo = Repo(repo_path)
                repo.remotes.origin.pull()
                logger.info(f"代码拉取成功: {kb_id}")

            return repo_path
        except Exception as e:
            logger.error(f"Git 操作失败: {e}")
            # 如果失败，删除缓存目录，下次重新克隆
            if repo_path.exists():
                shutil.rmtree(repo_path)
                logger.info(f"已删除缓存目录: {repo_path}")
            raise

    async def read_file(
        self,
        kb_id: str,
        file_path: str,
        repo_url: Optional[str] = None
    ) -> str:
        """
        读取文件内容

        Args:
            kb_id: 知识库 ID
            file_path: 文件路径（相对于仓库根目录）
            repo_url: 仓库 URL（可选，如果缓存不存在）

        Returns:
            文件内容

        Raises:
            FileNotFoundError: 文件不存在
            ValueError: 知识库未配置 Git 仓库
        """
        # 获取仓库元数据
        kb = await self._get_kb_info(kb_id)
        if not kb:
            raise FileNotFoundError(f"知识库 {kb_id} 不存在")

        if not repo_url:
            repo_url = kb.repository_url

        if not repo_url:
            raise ValueError(f"知识库 {kb_id} 没有配置 Git 仓库")

        # 确保已克隆
        repo_path = await self.ensure_cloned(repo_url, kb_id)

        # 读取文件
        full_path = repo_path / file_path
        if not full_path.exists():
            raise FileNotFoundError(f"文件不存在: {file_path}")

        content = full_path.read_text(encoding='utf-8')
        logger.info(f"读取文件成功: {kb_id}/{file_path} ({len(content)} 字符)")
        return content

    async def commit_file(
        self,
        kb_id: str,
        file_path: str,
        content: str,
        message: str,
        author: str,
        repo_url: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        提交文件变更到 Git 仓库

        Args:
            kb_id: 知识库 ID
            file_path: 文件路径
            content: 文件内容
            message: 提交信息
            author: 作者
            repo_url: 仓库 URL（可选）

        Returns:
            提交结果（包含 commit SHA）

        Raises:
            ValueError: 知识库未配置 Git 仓库
        """
        # 获取仓库 URL
        kb = await self._get_kb_info(kb_id)
        if kb and not repo_url:
            repo_url = kb.repository_url

        if not repo_url:
            raise ValueError(f"知识库 {kb_id} 没有配置 Git 仓库")

        # 确保已克隆
        repo_path = await self.ensure_cloned(repo_url, kb_id)
        repo = Repo(repo_path)

        # 写入文件
        full_path = repo_path / file_path
        full_path.parent.mkdir(parents=True, exist_ok=True)
        full_path.write_text(content, encoding='utf-8')

        logger.info(f"文件已写入: {full_path}")

        # Git 操作
        try:
            # 添加文件
            repo.git.add(A=True)

            # 检查是否有变更
            if repo.is_dirty(untracked_files=True):
                # 提交
                commit = repo.index.commit(
                    f"{message}\n\nAuthor: {author}",
                    author_date=datetime.now().isoformat()
                )

                # 推送
                origin = repo.remotes.origin
                origin.push()

                logger.info(f"提交成功: {commit.hexsha[:8]} - {message}")

                return {
                    "status": "success",
                    "commit": commit.hexsha,
                    "short_sha": commit.hexsha[:8],
                    "message": message
                }
            else:
                logger.info(f"文件无变更，跳过提交")
                return {
                    "status": "unchanged",
                    "message": "文件无变更"
                }
        except Exception as e:
            logger.error(f"Git 提交失败: {e}")
            raise

    async def get_history(
        self,
        kb_id: str,
        file_path: str,
        limit: int = 10,
        repo_url: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        获取文件历史记录

        Args:
            kb_id: 知识库 ID
            file_path: 文件路径
            limit: 返回记录数量
            repo_url: 仓库 URL

        Returns:
            历史记录列表

        Raises:
            ValueError: 知识库未配置 Git 仓库
        """
        # 获取仓库 URL
        kb = await self._get_kb_info(kb_id)
        if kb and not repo_url:
            repo_url = kb.repository_url

        if not repo_url:
            raise ValueError(f"知识库 {kb_id} 没有配置 Git 仓库")

        # 确保已克隆
        repo_path = await self.ensure_cloned(repo_url, kb_id)
        repo = Repo(repo_path)

        # 获取文件历史
        commits = list(repo.iter_commits(paths=file_path, max_count=limit))

        history = [
            {
                "sha": commit.hexsha,
                "short_sha": commit.hexsha[:8],
                "message": commit.message.strip(),
                "author": commit.author.name,
                "date": datetime.fromtimestamp(commit.committed_date).isoformat(),
                "full_date": commit.committed_datetime.isoformat()
            }
            for commit in commits
        ]

        logger.info(f"获取历史记录: {kb_id}/{file_path} ({len(history)} 条)")
        return history

    async def get_diff(
        self,
        kb_id: str,
        file_path: str,
        commit_a: Optional[str] = None,
        commit_b: Optional[str] = None,
        repo_url: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        获取文件 diff

        Args:
            kb_id: 知识库 ID
            file_path: 文件路径
            commit_a: 旧版本 SHA（可选，默认为 HEAD~1）
            commit_b: 新版本 SHA（可选，默认为 HEAD）
            repo_url: 仓库 URL

        Returns:
            Diff 结果

        Raises:
            ValueError: 知识库未配置 Git 仓库
        """
        # 获取仓库 URL
        kb = await self._get_kb_info(kb_id)
        if kb and not repo_url:
            repo_url = kb.repository_url

        if not repo_url:
            raise ValueError(f"知识库 {kb_id} 没有配置 Git 仓库")

        # 确保已克隆
        repo_path = await self.ensure_cloned(repo_url, kb_id)
        repo = Repo(repo_path)

        # 获取 diff
        if commit_b is None:
            commit_b = 'HEAD'
        if commit_a is None:
            commit_a = f'{commit_b}~1'

        try:
            diff = repo.git.diff(f"{commit_a}:{file_path}", f"{commit_b}:{file_path}")

            result = {
                "file_path": file_path,
                "commit_a": commit_a,
                "commit_b": commit_b,
                "diff": diff
            }

            logger.info(f"获取 diff: {kb_id}/{file_path} ({commit_a}..{commit_b})")
            return result
        except Exception as e:
            logger.error(f"获取 diff 失败: {e}")
            return {
                "file_path": file_path,
                "commit_a": commit_a,
                "commit_b": commit_b,
                "diff": "",
                "error": str(e)
            }

    async def create_branch(
        self,
        kb_id: str,
        branch_name: str,
        from_branch: str = "main",
        repo_url: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        创建新分支

        Args:
            kb_id: 知识库 ID
            branch_name: 新分支名称
            from_branch: 基于哪个分支
            repo_url: 仓库 URL

        Returns:
            创建结果

        Raises:
            ValueError: 知识库未配置 Git 仓库
        """
        # 获取仓库 URL
        kb = await self._get_kb_info(kb_id)
        if kb and not repo_url:
            repo_url = kb.repository_url

        if not repo_url:
            raise ValueError(f"知识库 {kb_id} 没有配置 Git 仓库")

        # 确保已克隆
        repo_path = await self.ensure_cloned(repo_url, kb_id)
        repo = Repo(repo_path)

        # 创建新分支
        new_branch = repo.create_head(branch_name, commit=f'refs/heads/{from_branch}')

        # 推送到远程
        repo.git.push('origin', f'{branch_name}:{branch_name}')

        logger.info(f"创建分支成功: {branch_name} (基于 {from_branch})")

        return {
            "status": "success",
            "branch": branch_name,
            "from": from_branch
        }

    async def get_status(
        self,
        kb_id: str,
        repo_url: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        获取仓库状态

        Args:
            kb_id: 知识库 ID
            repo_url: 仓库 URL

        Returns:
            仓库状态信息
        """
        # 获取仓库 URL
        kb = await self._get_kb_info(kb_id)
        if kb and not repo_url:
            repo_url = kb.repository_url

        if not repo_url:
            return {
                "kb_id": kb_id,
                "is_repo": False,
                "error": "未配置 Git 仓库"
            }

        # 检查本地缓存
        repo_path = self._get_repo_path(kb_id)
        if not repo_path.exists():
            return {
                "kb_id": kb_id,
                "is_repo": False,
                "cached": False,
                "repository_url": repo_url
            }

        try:
            repo = Repo(repo_path)
            return {
                "kb_id": kb_id,
                "is_repo": True,
                "cached": True,
                "repository_url": repo_url,
                "branch": repo.active_branch.name,
                "head": repo.head.commit.hexsha[:8],
                "dirty": repo.is_dirty(),
                "untracked_files": len(repo.untracked_files),
                "modified_files": len([item.a_path for item in repo.index.diff(None)])
            }
        except Exception as e:
            logger.error(f"获取仓库状态失败: {e}")
            return {
                "kb_id": kb_id,
                "is_repo": False,
                "error": str(e)
            }
