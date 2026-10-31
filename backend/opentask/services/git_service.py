"""Git 服务 - 知识库 Git 仓库管理"""
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List

from git import Repo, Actor, GitCommandError
from sqlalchemy.ext.asyncio import AsyncSession

from opentask.services.file_storage import FileStorageService

logger = logging.getLogger(__name__)


class GitService:
    """Git 服务 - 管理知识库的 Git 仓库"""

    def __init__(self, storage: FileStorageService):
        """
        初始化 Git 服务

        Args:
            storage: 文件存储服务
        """
        self.storage = storage

    def init_repo(self, kb_id: str) -> Repo:
        """
        初始化知识库 Git 仓库

        Args:
            kb_id: 知识库 ID

        Returns:
            Repo: Git 仓库对象
        """
        repo_path = self.storage.get_knowledge_base_dir(kb_id)

        # 检查是否已经是 Git 仓库
        git_dir = os.path.join(repo_path, '.git')
        if os.path.exists(git_dir):
            logger.info(f"知识库 {kb_id} 已经是 Git 仓库")
            return Repo(repo_path)

        # 初始化仓库
        logger.info(f"初始化知识库 {kb_id} 的 Git 仓库")
        repo = Repo.init(repo_path, initial_branch='main')

        # 创建 .gitignore
        gitignore_path = os.path.join(repo_path, '.gitignore')
        with open(gitignore_path, 'w', encoding='utf-8') as f:
            f.write('# 元数据文件（由系统管理）\n')
            f.write('.meta.json\n')
            f.write('\n# 缩略图和缓存\n')
            f.write('assets/.thumbnails/\n')
            f.write('.DS_Store\n')
            f.write('\n# 临时文件\n')
            f.write('*.tmp\n')
            f.write('*~\n')
            f.write('.*.swp\n')

        # 初始提交
        if repo.is_dirty(untracked_files=True):
            repo.git.add(A=True)
            repo.index.commit(
                "feat: 初始化知识库 Git 仓库\n\n建立文件优先架构的知识库系统",
                author=Actor("system", "system@opentask")
            )
            logger.info(f"知识库 {kb_id} Git 仓库初始化完成")

        return repo

    def get_repo(self, kb_id: str) -> Optional[Repo]:
        """
        获取知识库的 Git 仓库

        Args:
            kb_id: 知识库 ID

        Returns:
            Repo: Git 仓库对象，如果不存在返回 None
        """
        repo_path = self.storage.get_knowledge_base_dir(kb_id)
        git_dir = os.path.join(repo_path, '.git')

        if not os.path.exists(git_dir):
            logger.warning(f"知识库 {kb_id} 不是 Git 仓库")
            return None

        try:
            return Repo(repo_path)
        except Exception as e:
            logger.error(f"获取 Git 仓库失败 {kb_id}: {e}")
            return None

    def commit_changes(
        self,
        kb_id: str,
        message: str,
        author: str = "system",
        author_email: str = "system@opentask"
    ) -> Optional[str]:
        """
        提交变更到 Git 仓库

        Args:
            kb_id: 知识库 ID
            message: 提交消息
            author: 作者
            author_email: 作者邮箱

        Returns:
            str: 提交的 hash，如果失败返回 None
        """
        repo = self.get_repo(kb_id)
        if not repo:
            logger.error(f"知识库 {kb_id} 不是 Git 仓库")
            return None

        try:
            # 检查是否有变更
            if not repo.is_dirty(untracked_files=True):
                logger.info(f"知识库 {kb_id} 没有变更需要提交")
                return repo.head.commit.hexsha if repo.heads else None

            # 添加所有变更
            repo.git.add(A=True)

            # 提交
            commit = repo.index.commit(
                message,
                author=Actor(author, author_email)
            )

            logger.info(f"知识库 {kb_id} 提交成功: {commit.hexsha[:8]}")
            return commit.hexsha

        except GitCommandError as e:
            logger.error(f"Git 提交失败 {kb_id}: {e}")
            return None

    def has_changes(self, kb_id: str) -> bool:
        """
        检查知识库是否有未提交的变更

        Args:
            kb_id: 知识库 ID

        Returns:
            bool: 是否有变更
        """
        repo = self.get_repo(kb_id)
        if not repo:
            return False

        return repo.is_dirty(untracked_files=True)

    def get_history(
        self,
        kb_id: str,
        doc_id: Optional[str] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
       获取提交历史

        Args:
            kb_id: 知识库 ID
            doc_id: 文档 ID（可选，如果指定则只返回该文档的历史）
            limit: 返回数量限制

        Returns:
            List[Dict]: 提交历史列表
        """
        repo = self.get_repo(kb_id)
        if not repo:
            return []

        try:
            if doc_id:
                # 获取特定文档的历史
                doc_path = self.storage.get_doc_file_path(kb_id, doc_id)
                if not doc_path.exists():
                    return []

                # 获取相对于 repo 的路径
                rel_path = os.path.relpath(doc_path, repo.working_dir)
                commits = list(repo.iter_commits(paths=rel_path, max_count=limit))
            else:
                # 获取整个仓库的历史
                commits = list(repo.iter_commits(max_count=limit))

            result = []
            for commit in commits:
                result.append({
                    "hash": commit.hexsha,
                    "short_hash": commit.hexsha[:8],
                    "message": commit.message.strip(),
                    "author": str(commit.author),
                    "date": datetime.fromtimestamp(commit.committed_date),
                    "parents": [p.hexsha for p in commit.parents]
                })

            return result

        except Exception as e:
            logger.error(f"获取 Git 历史失败 {kb_id}: {e}")
            return []

    def get_diff(
        self,
        kb_id: str,
        doc_id: str,
        commit_hash: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        获取文档的 diff

        Args:
            kb_id: 知识库 ID
            doc_id: 文档 ID
            commit_hash: 提交 hash（可选，如果不指定则与工作区比较）

        Returns:
            Dict: diff 信息
        """
        repo = self.get_repo(kb_id)
        if not repo:
            return None

        try:
            doc_path = self.storage.get_doc_file_path(kb_id, doc_id)
            if not doc_path.exists():
                return None

            # 获取相对于 repo 的路径
            rel_path = os.path.relpath(doc_path, repo.working_dir)

            if commit_hash:
                # 与指定提交比较
                commit = repo.commit(commit_hash)
                parent = commit.parents[0] if commit.parents else None

                if parent:
                    diff = parent.diff(commit, paths=rel_path)
                else:
                    # 初始提交
                    diff = commit.diff(None, paths=rel_path, create_patch=True)
            else:
                # 与工作区比较（未提交的变更）
                if repo.is_dirty():
                    diff = repo.index.diff(None, paths=rel_path)
                else:
                    return None

            # 解析 diff
            diffs = []
            for diff_item in diff:
                diffs.append({
                    "a_path": diff_item.a_path,
                    "b_path": diff_item.b_path,
                    "change_type": diff_item.change_type,
                    "diff": diff_item.diff.decode('utf-8') if diff_item.diff else ''
                })

            return {
                "doc_id": doc_id,
                "commit_hash": commit_hash,
                "diffs": diffs
            }

        except Exception as e:
            logger.error(f"获取 diff 失败 {kb_id}/{doc_id}: {e}")
            return None

    def create_branch(
        self,
        kb_id: str,
        branch_name: str,
        start_point: Optional[str] = None
    ) -> bool:
        """
        创建分支

        Args:
            kb_id: 知识库 ID
            branch_name: 分支名称
            start_point: 起始提交（可选）

        Returns:
            bool: 是否成功
        """
        repo = self.get_repo(kb_id)
        if not repo:
            return False

        try:
            if start_point:
                repo.create_head(branch_name, start_point)
            else:
                repo.create_head(branch_name)

            logger.info(f"知识库 {kb_id} 创建分支 {branch_name} 成功")
            return True

        except Exception as e:
            logger.error(f"创建分支失败 {kb_id}/{branch_name}: {e}")
            return False

    def list_branches(self, kb_id: str) -> List[Dict[str, Any]]:
        """
       列出所有分支

        Args:
            kb_id: 知识库 ID

        Returns:
            List[Dict]: 分支列表
        """
        repo = self.get_repo(kb_id)
        if not repo:
            return []

        try:
            branches = []
            for head in repo.heads:
                commit = head.commit
                branches.append({
                    "name": head.name,
                    "commit_hash": commit.hexsha,
                    "short_hash": commit.hexsha[:8],
                    "message": commit.message.strip(),
                    "is_active": head == repo.head
                })

            return branches

        except Exception as e:
            logger.error(f"获取分支列表失败 {kb_id}: {e}")
            return []

    def get_status(self, kb_id: str) -> Dict[str, Any]:
        """
        获取仓库状态

        Args:
            kb_id: 知识库 ID

        Returns:
            Dict: 状态信息
        """
        repo = self.get_repo(kb_id)
        if not repo:
            return {
                "kb_id": kb_id,
                "is_repo": False,
                "branch": None,
                "dirty": False,
                "untracked": 0,
                "modified": 0,
                "staged": 0
            }

        try:
            # 获取当前分支
            branch = repo.active_branch.name if repo.active_branch else None

            # 获取变更文件
            changed_files = repo.index.diff(None)
            untracked_files = repo.untracked_files

            # 统计
            modified = len([f for f in changed_files if f.change_type in ['M', 'R']])
            staged = len([f for f in repo.index.diff('HEAD') if f.change_type in ['M', 'R', 'A']])
            untracked = len(untracked_files)

            return {
                "kb_id": kb_id,
                "is_repo": True,
                "branch": branch,
                "dirty": repo.is_dirty(),
                "untracked": untracked,
                "modified": modified,
                "staged": staged,
                "current_commit": repo.head.commit.hexsha if repo.heads else None
            }

        except Exception as e:
            logger.error(f"获取仓库状态失败 {kb_id}: {e}")
            return {
                "kb_id": kb_id,
                "is_repo": False,
                "error": str(e)
            }
