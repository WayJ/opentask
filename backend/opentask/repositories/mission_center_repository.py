"""Agent Task Repository 数据访问层"""

from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime, timedelta
from sqlalchemy import select, update, delete, func, and_, desc
from sqlalchemy.ext.asyncio import AsyncSession

from opentask.models.mission_center import AgentTask, AgentWallet, AgentTransaction
from opentask.repositories.base import NotFoundError
from opentask.services.user_center.rbac_service import RbacService


class AgentTaskRepository:
    """Agent 任务数据访问层"""

    async def create_task(
        self,
        session: AsyncSession,
        task_id: str,
        title: str,
        description: str,
        priority: str,
        assignee: Optional[str],
        deadline: Optional[str],
        metadata: Optional[Dict[str, Any]],
        requirements: Optional[List[str]],
        acceptance_criteria: Optional[List[str]],
        reward: int,
        dept_id: Optional[str] = None,
    ) -> AgentTask:
        """创建新任务

        dept_id: 创建人主部门 id 快照（None 表示无归属/系统创建，行保持 NULL）
        """
        task = AgentTask(
            task_id=task_id,
            title=title,
            description=description,
            priority=priority,
            assignee=assignee,
            deadline=datetime.fromisoformat(deadline) if deadline else None,
            metadata=metadata or {},
            requirements=requirements or [],
            acceptance_criteria=acceptance_criteria or [],
            reward=reward,
            dept_id=dept_id,  # 部门归属快照
        )
        session.add(task)
        await session.flush()
        return task

    async def get_task(self, session: AsyncSession, task_id: str) -> Optional[AgentTask]:
        """获取任务"""
        stmt = select(AgentTask).where(AgentTask.task_id == task_id)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_tasks(
        self,
        session: AsyncSession,
        status: Optional[str] = None,
        assignee: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
        visible_dept_ids: set[str] | None = None,
    ) -> List[AgentTask]:
        """列出任务

        visible_dept_ids: 数据范围可见部门集（None=不过滤，空集=SELF 结果恒空）
        """
        stmt = select(AgentTask)

        # 过滤条件
        conditions = []
        if status:
            conditions.append(AgentTask.status == status)
        if assignee:
            conditions.append(AgentTask.assignee == assignee)

        if conditions:
            stmt = stmt.where(and_(*conditions))

        # 数据范围过滤（visible_dept_ids=None 时原样返回，旧调用零破坏）
        stmt = RbacService(session=None).apply_data_scope(
            stmt,
            visible_dept_ids,
            dept_col=AgentTask.dept_id,
        )

        # 排序和分页
        stmt = stmt.order_by(desc(AgentTask.updated_at)).offset(offset).limit(limit)

        result = await session.execute(stmt)
        return list(result.scalars().all())

    async def count_tasks(
        self,
        session: AsyncSession,
        status: Optional[str] = None,
        assignee: Optional[str] = None,
    ) -> int:
        """统计任务数量"""
        stmt = select(func.count(AgentTask.task_id))

        # 过滤条件
        conditions = []
        if status:
            conditions.append(AgentTask.status == status)
        if assignee:
            conditions.append(AgentTask.assignee == assignee)

        if conditions:
            stmt = stmt.where(and_(*conditions))

        result = await session.execute(stmt)
        return result.scalar_one()

    async def update_task_status(
        self,
        session: AsyncSession,
        task_id: str,
        status: str,
        progress_percentage: int,
        current_step: str,
        logs: Optional[List[Dict[str, str]]] = None,
        progress_history_entry: Optional[Dict[str, Any]] = None,
        assignee: Optional[str] = None,
    ) -> Optional[AgentTask]:
        """更新任务状态"""
        task = await self.get_task(session, task_id)
        if not task:
            return None

        # 更新字段
        task.status = status
        task.progress_percentage = progress_percentage
        task.current_step = current_step
        task.updated_at = datetime.utcnow()

        if assignee:
            task.assignee = assignee

        if progress_history_entry:
            if task.progress_history is None:
                task.progress_history = []
            task.progress_history.append(progress_history_entry)

        if logs:
            if task.logs is None:
                task.logs = []
            task.logs.extend(logs)

        # 如果任务完成或失败，记录完成时间
        if status in ["completed", "failed", "cancelled"]:
            task.completed_at = datetime.utcnow()

        await session.flush()
        return task

    async def delete_task(self, session: AsyncSession, task_id: str) -> bool:
        """删除任务"""
        task = await self.get_task(session, task_id)
        if not task:
            return False

        await session.delete(task)
        return True

    async def get_statistics(self, session: AsyncSession) -> Dict[str, Any]:
        """获取任务统计"""
        # 总数统计
        total_stmt = select(func.count(AgentTask.task_id))
        total_result = await session.execute(total_stmt)
        total = total_result.scalar_one()

        # 按状态统计
        status_stats = {}
        for status_value in ["pending", "assigned", "in_progress", "completed", "failed", "cancelled", "blocked"]:
            stmt = select(func.count(AgentTask.task_id)).where(AgentTask.status == status_value)
            result = await session.execute(stmt)
            status_stats[status_value] = result.scalar_one()

        # 按优先级统计
        priority_stats = {}
        for priority_value in ["low", "medium", "high", "urgent"]:
            stmt = select(func.count(AgentTask.task_id)).where(AgentTask.priority == priority_value)
            result = await session.execute(stmt)
            priority_stats[priority_value] = result.scalar_one()

        return {
            "total": total,
            "by_status": status_stats,
            "by_priority": priority_stats,
        }

    async def count_active_tasks_for_agent(
        self,
        session: AsyncSession,
        agent_id: str,
    ) -> int:
        """统计 Agent 的活跃任务数量（ASSIGNED 或 IN_PROGRESS 状态）"""
        stmt = select(func.count(AgentTask.task_id)).where(
            and_(
                AgentTask.assignee == agent_id,
                AgentTask.status.in_(["assigned", "in_progress"])
            )
        )
        result = await session.execute(stmt)
        return result.scalar_one()

    async def get_stale_tasks(
        self,
        session: AsyncSession,
        timeout_hours: int = 1,
    ) -> List[AgentTask]:
        """获取超时的活跃任务（超过指定小时未更新）"""
        timeout_threshold = datetime.utcnow() - timedelta(hours=timeout_hours)

        stmt = select(AgentTask).where(
            and_(
                AgentTask.status.in_(["assigned", "in_progress"]),
                AgentTask.updated_at < timeout_threshold
            )
        )

        result = await session.execute(stmt)
        return list(result.scalars().all())


class AgentWalletRepository:
    """Agent 钱包数据访问层"""

    async def get_or_create_wallet(self, session: AsyncSession, agent_id: str) -> AgentWallet:
        """获取或创建钱包"""
        wallet = await self.get_wallet(session, agent_id)
        if not wallet:
            wallet = AgentWallet(agent_id=agent_id)
            session.add(wallet)
            await session.flush()
        return wallet

    async def get_wallet(self, session: AsyncSession, agent_id: str) -> Optional[AgentWallet]:
        """获取钱包"""
        stmt = select(AgentWallet).where(AgentWallet.agent_id == agent_id)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_all_wallets(self, session: AsyncSession) -> List[AgentWallet]:
        """获取所有钱包"""
        stmt = select(AgentWallet).order_by(desc(AgentWallet.balance))
        result = await session.execute(stmt)
        return list(result.scalars().all())

    async def update_balance(
        self,
        session: AsyncSession,
        agent_id: str,
        amount: int,
    ) -> AgentWallet:
        """更新钱包余额"""
        wallet = await self.get_or_create_wallet(session, agent_id)

        wallet.balance += amount
        if amount > 0:
            wallet.total_earned += amount
        else:
            wallet.total_spent += abs(amount)

        wallet.updated_at = datetime.utcnow()
        await session.flush()
        return wallet

    async def create_transaction(
        self,
        session: AsyncSession,
        agent_id: str,
        amount: int,
        transaction_type: str,
        description: str,
        related_task_id: Optional[str] = None,
    ) -> AgentTransaction:
        """创建交易"""
        # 先更新钱包余额
        wallet = await self.update_balance(session, agent_id, amount)

        # 创建交易记录
        transaction = AgentTransaction(
            agent_id=agent_id,
            amount=amount,
            balance_after=wallet.balance,
            transaction_type=transaction_type,
            description=description,
            related_task_id=related_task_id,
        )
        session.add(transaction)
        await session.flush()
        return transaction

    async def get_transactions(
        self,
        session: AsyncSession,
        agent_id: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[List[AgentTransaction], int]:
        """获取交易列表"""
        # 统计总数
        count_stmt = select(func.count(AgentTransaction.id))
        if agent_id:
            count_stmt = count_stmt.where(AgentTransaction.agent_id == agent_id)
        count_result = await session.execute(count_stmt)
        total = count_result.scalar_one()

        # 获取交易列表
        stmt = select(AgentTransaction)
        if agent_id:
            stmt = stmt.where(AgentTransaction.agent_id == agent_id)

        stmt = stmt.order_by(desc(AgentTransaction.created_at)).offset(offset).limit(limit)

        result = await session.execute(stmt)
        transactions = list(result.scalars().all())

        return transactions, total

    async def get_statistics(self, session: AsyncSession) -> Dict[str, Any]:
        """获取钱包统计"""
        # 总余额
        total_balance_stmt = select(func.sum(AgentWallet.balance))
        total_balance_result = await session.execute(total_balance_stmt)
        total_balance = total_balance_result.scalar_one() or 0

        # 总获得
        total_earned_stmt = select(func.sum(AgentWallet.total_earned))
        total_earned_result = await session.execute(total_earned_stmt)
        total_earned = total_earned_result.scalar_one() or 0

        # 总消费
        total_spent_stmt = select(func.sum(AgentWallet.total_spent))
        total_spent_result = await session.execute(total_spent_stmt)
        total_spent = total_spent_result.scalar_one() or 0

        # 交易总数
        transaction_count_stmt = select(func.count(AgentTransaction.id))
        transaction_count_result = await session.execute(transaction_count_stmt)
        transaction_count = transaction_count_result.scalar_one()

        # 活跃钱包数
        active_wallets_stmt = select(func.count(AgentWallet.agent_id)).where(AgentWallet.balance > 0)
        active_wallets_result = await session.execute(active_wallets_stmt)
        active_wallets = active_wallets_result.scalar_one()

        return {
            "total_balance": total_balance,
            "total_earned": total_earned,
            "total_spent": total_spent,
            "transaction_count": transaction_count,
            "active_wallets": active_wallets,
        }
