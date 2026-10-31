"""自动提交服务 - 定期提交知识库变更到 Git"""
import asyncio
import logging
from datetime import datetime
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from opentask.models.knowledge_base.model import KnowledgeBase
from opentask.services.git_service import GitService

logger = logging.getLogger(__name__)


class AutoCommitService:
    """自动提交服务"""

    def __init__(
        self,
        db: AsyncSession,
        git_service: GitService,
        interval: int = 300,
        enabled: bool = True
    ):
        """
        初始化自动提交服务

        Args:
            db: 数据库会话
            git_service: Git 服务
            interval: 提交间隔（秒），默认 300 秒（5 分钟）
            enabled: 是否启用
        """
        self.db = db
        self.git_service = git_service
        self.interval = interval
        self.enabled = enabled
        self.running = False
        self.task: Optional[asyncio.Task] = None

    async def start(self):
        """启动自动提交服务"""
        if self.running:
            logger.warning("自动提交服务已在运行")
            return

        if not self.enabled:
            logger.info("自动提交服务未启用")
            return

        self.running = True
        logger.info(f"自动提交服务已启动（间隔: {self.interval}秒）")

        while self.running:
            try:
                await asyncio.sleep(self.interval)
                await self.commit_all_changes()
            except Exception as e:
                logger.error(f"自动提交失败: {e}")

    def stop(self):
        """停止自动提交服务"""
        self.running = False
        logger.info("自动提交服务已停止")

    async def commit_all_changes(self):
        """提交所有知识库的变更"""
        try:
            # 获取所有启用了 Git 的知识库
            result = await self.db.execute(
                select(KnowledgeBase).where(
                    KnowledgeBase.status == 'active'
                )
            )
            knowledge_bases = result.scalars().all()

            committed_count = 0
            for kb in knowledge_bases:
                try:
                    # 检查是否是 Git 仓库
                    repo = self.git_service.get_repo(kb.id)
                    if not repo:
                        continue

                    # 检查是否有变更
                    if self.git_service.has_changes(kb.id):
                        # 生成提交消息
                        message = self._generate_commit_message(kb.id)

                        # 提交变更
                        commit_hash = self.git_service.commit_changes(
                            kb.id,
                            message,
                            author="system",
                            author_email="system@opentask"
                        )

                        if commit_hash:
                            committed_count += 1
                            logger.info(f"自动提交成功: {kb.id} - {commit_hash[:8]}")

                except Exception as e:
                    logger.error(f"提交知识库 {kb.id} 失败: {e}")

            if committed_count > 0:
                logger.info(f"自动提交完成: {committed_count} 个知识库")
            else:
                logger.debug("没有需要提交的变更")

        except Exception as e:
            logger.error(f"批量提交失败: {e}")

    def _generate_commit_message(self, kb_id: str) -> str:
        """
        生成提交消息

        Args:
            kb_id: 知识库 ID

        Returns:
            str: 提交消息
        """
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        return f"auto: 自动提交 - {timestamp}\n\n系统自动提交知识库变更"

    async def commit_single_kb(self, kb_id: str, message: Optional[str] = None) -> bool:
        """
        提交单个知识库的变更

        Args:
            kb_id: 知识库 ID
            message: 提交消息（可选）

        Returns:
            bool: 是否成功
        """
        try:
            # 检查是否是 Git 仓库
            repo = self.git_service.get_repo(kb_id)
            if not repo:
                logger.warning(f"知识库 {kb_id} 不是 Git 仓库")
                return False

            # 检查是否有变更
            if not self.git_service.has_changes(kb_id):
                logger.info(f"知识库 {kb_id} 没有变更需要提交")
                return True

            # 生成提交消息
            if not message:
                message = self._generate_commit_message(kb_id)

            # 提交变更
            commit_hash = self.git_service.commit_changes(
                kb_id,
                message,
                author="system",
                author_email="system@opentask"
            )

            if commit_hash:
                logger.info(f"提交成功: {kb_id} - {commit_hash[:8]}")
                return True
            else:
                return False

        except Exception as e:
            logger.error(f"提交知识库 {kb_id} 失败: {e}")
            return False

    def is_running(self) -> bool:
        """检查服务是否在运行"""
        return self.running
