"""
Agent Task Comment Repository
评论数据访问层
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, func

from opentask.models.mission_center import AgentTask, AgentTaskComment


class AgentTaskCommentRepository:
    """任务评论 Repository"""

    async def create_comment(
        self,
        session: AsyncSession,
        task_id: str,
        content: str,
        comment_type: str = "comment",
        agent_id: str = None,
        user_id: str = None,
        parent_id: int = None
    ) -> AgentTaskComment:
        """创建评论"""
        comment = AgentTaskComment(
            task_id=task_id,
            content=content,
            comment_type=comment_type,
            agent_id=agent_id,
            user_id=user_id,
            parent_id=parent_id
        )

        session.add(comment)
        await session.flush()

        return comment

    async def get_comments(
        self,
        session: AsyncSession,
        task_id: str,
        limit: int = 50,
        offset: int = 0
    ) -> list[AgentTaskComment]:
        """获取任务的所有评论"""
        stmt = (
            select(AgentTaskComment)
            .where(AgentTaskComment.task_id == task_id)
            .order_by(AgentTaskComment.created_at.asc())
            .limit(limit)
            .offset(offset)
        )

        result = await session.execute(stmt)
        return list(result.scalars())

    async def get_comment_count(
        self,
        session: AsyncSession,
        task_id: str
    ) -> int:
        """获取评论数量"""
        stmt = (
            select(func.count(AgentTaskComment.id))
            .where(AgentTaskComment.task_id == task_id)
        )

        result = await session.execute(stmt)
        return result.scalar() or 0

    async def delete_comment(
        self,
        session: AsyncSession,
        comment_id: int
    ) -> bool:
        """删除评论"""
        stmt = select(AgentTaskComment).where(AgentTaskComment.id == comment_id)
        result = await session.execute(stmt)
        comment = result.scalar_one_or_none()

        if comment:
            await session.delete(comment)
            return True
        return False
