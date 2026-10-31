"""
OpenTask 任务管理服务

提供任务的 CRUD 操作、状态管理和进度跟踪
使用数据库持久化存储
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum
import uuid
from sqlalchemy.ext.asyncio import AsyncSession

from opentask.repositories.mission_center_repository import AgentTaskRepository, AgentWalletRepository
from opentask.repositories.base import SessionCreator, get_session


class TaskPriority(str, Enum):
    """任务优先级"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class TaskStatus(str, Enum):
    """任务状态"""
    PENDING = "pending"
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class Task:
    """任务实体（内存中表示）"""

    def __init__(
        self,
        task_id: str,
        title: str,
        description: str,
        priority: TaskPriority,
        assignee: Optional[str] = None,
        deadline: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        requirements: Optional[List[str]] = None,
        acceptance_criteria: Optional[List[str]] = None,
        reward: Optional[int] = None,
        status: TaskStatus = TaskStatus.PENDING,
        progress_percentage: int = 0,
        current_step: str = "",
        created_at: Optional[str] = None,
        updated_at: Optional[str] = None,
        completed_at: Optional[str] = None,
        result: Optional[Dict[str, Any]] = None,
        error: Optional[Dict[str, Any]] = None,
        logs: Optional[List[Dict[str, str]]] = None,
        progress_history: Optional[List[Dict[str, Any]]] = None,
        execution_time_ms: Optional[int] = None,
        link_data: Optional[List[str]] = None,  # 添加link_data参数
    ):
        self.task_id = task_id
        self.title = title
        self.description = description
        self.priority = priority if isinstance(priority, TaskPriority) else TaskPriority(priority)
        self.assignee = assignee
        self.deadline = deadline
        self.metadata = metadata or {}
        self.requirements = requirements or []
        self.acceptance_criteria = acceptance_criteria or []
        self.reward = reward or 0

        # 状态字段
        self.status = status if isinstance(status, TaskStatus) else TaskStatus(status)
        self.progress_percentage = progress_percentage
        self.current_step = current_step
        self.created_at = created_at or datetime.utcnow().isoformat()
        self.updated_at = updated_at or datetime.utcnow().isoformat()
        self.completed_at = completed_at

        # 执行结果
        self.result = result
        self.error = error
        self.logs = logs or []

        # 进度历史记录
        self.progress_history = progress_history or []

        # 执行统计
        self.execution_time_ms = execution_time_ms

        # 关联数据
        self.link_data = link_data or []

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "task_id": self.task_id,
            "title": self.title,
            "description": self.description,
            "priority": self.priority.value,
            "assignee": self.assignee,
            "deadline": self.deadline,
            "metadata": self.metadata,
            "requirements": self.requirements,
            "acceptance_criteria": self.acceptance_criteria,
            "reward": self.reward,
            "status": self.status.value,
            "progress_percentage": self.progress_percentage,
            "current_step": self.current_step,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "completed_at": self.completed_at,
            "result": self.result,
            "error": self.error,
            "logs": self.logs,
            "execution_time_ms": self.execution_time_ms,
            "progressHistory": self.progress_history,
            "link_data": self.link_data,  # 添加link_data
        }

    @classmethod
    def from_db_model(cls, db_task) -> "Task":
        """从数据库模型创建 Task 实体"""
        return cls(
            task_id=db_task.task_id,
            title=db_task.title,
            description=db_task.description or "",
            priority=db_task.priority,
            assignee=db_task.assignee,
            deadline=db_task.deadline.isoformat() if db_task.deadline else None,
            metadata=db_task.meta_data or {},  # 使用 meta_data 属性
            requirements=db_task.requirements or [],
            acceptance_criteria=db_task.acceptance_criteria or [],
            reward=db_task.reward,
            status=db_task.status,
            progress_percentage=db_task.progress_percentage,
            current_step=db_task.current_step,
            created_at=db_task.created_at.isoformat() if db_task.created_at else None,
            updated_at=db_task.updated_at.isoformat() if db_task.updated_at else None,
            completed_at=db_task.completed_at.isoformat() if db_task.completed_at else None,
            result=db_task.result,
            error=db_task.error,
            logs=db_task.logs or [],
            progress_history=db_task.progress_history or [],
            execution_time_ms=db_task.execution_time_ms,
            link_data=db_task.link_data or [],  # 添加link_data
        )


class TaskService:
    """任务管理服务（使用数据库）"""

    def __init__(self):
        self._task_repo = AgentTaskRepository()

    async def create_task(
        self,
        title: str,
        description: str,
        priority: TaskPriority,
        assignee: Optional[str] = None,
        deadline: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        requirements: Optional[List[str]] = None,
        acceptance_criteria: Optional[List[str]] = None,
        reward: Optional[int] = None,
        dept_id: Optional[str] = None,
    ) -> Task:
        """创建新任务

        dept_id: 创建人主部门 id 快照（None 表示无归属，行保持 NULL）
        """
        task_id = f"task_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{str(uuid.uuid4())[:8]}"

        async with SessionCreator() as session:
            db_task = await self._task_repo.create_task(
                session=session,
                task_id=task_id,
                title=title,
                description=description,
                priority=priority.value,
                assignee=assignee,
                deadline=deadline,
                metadata=metadata,
                requirements=requirements,
                acceptance_criteria=acceptance_criteria,
                reward=reward or 0,
                dept_id=dept_id,
            )
            await session.commit()

        return Task.from_db_model(db_task)

    async def get_task(self, task_id: str) -> Optional[Task]:
        """获取任务"""
        async with SessionCreator() as session:
            db_task = await self._task_repo.get_task(session, task_id)
            if not db_task:
                return None
            return Task.from_db_model(db_task)

    async def list_tasks(
        self,
        status: Optional[TaskStatus] = None,
        assignee: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
        visible_dept_ids: set[str] | None = None,
    ) -> List[Task]:
        """列出任务

        visible_dept_ids: 数据范围可见部门集（None=不过滤，空集=SELF 结果恒空）
        """
        async with SessionCreator() as session:
            db_tasks = await self._task_repo.list_tasks(
                session=session,
                status=status.value if status else None,
                assignee=assignee,
                limit=limit,
                offset=offset,
                visible_dept_ids=visible_dept_ids,
            )
            return [Task.from_db_model(t) for t in db_tasks]

    async def update_task_status(
        self,
        task_id: str,
        status: TaskStatus,
        progress_percentage: int = 0,
        current_step: str = "",
        logs: Optional[List[Dict[str, str]]] = None,
        progress_history_entry: Optional[Dict[str, Any]] = None,
        assignee: Optional[str] = None,
    ) -> Optional[Task]:
        """更新任务状态"""
        async with SessionCreator() as session:
            db_task = await self._task_repo.update_task_status(
                session=session,
                task_id=task_id,
                status=status.value,
                progress_percentage=progress_percentage,
                current_step=current_step,
                logs=logs,
                progress_history_entry=progress_history_entry,
                assignee=assignee,
            )
            if not db_task:
                return None
            await session.commit()
            return Task.from_db_model(db_task)

    async def complete_task(
        self,
        task_id: str,
        result: Dict[str, Any],
        execution_time_ms: Optional[int] = None,
    ) -> Optional[Task]:
        """完成任务"""
        async with SessionCreator() as session:
            db_task = await self._task_repo.update_task_status(
                session=session,
                task_id=task_id,
                status=TaskStatus.COMPLETED.value,
                progress_percentage=100,
                current_step="已完成",
            )
            if not db_task:
                return None

            db_task.result = result
            db_task.execution_time_ms = execution_time_ms
            await session.commit()

            return Task.from_db_model(db_task)

    async def fail_task(
        self,
        task_id: str,
        error_code: str,
        error_message: str,
        retry_possible: bool = False,
    ) -> Optional[Task]:
        """标记任务失败"""
        async with SessionCreator() as session:
            db_task = await self._task_repo.get_task(session, task_id)
            if not db_task:
                return None

            db_task.status = TaskStatus.FAILED.value
            db_task.error = {
                "code": error_code,
                "message": error_message,
                "retry_possible": retry_possible,
            }
            await session.commit()

            return Task.from_db_model(db_task)

    async def cancel_task(self, task_id: str, reason: str = "") -> Optional[Task]:
        """取消任务"""
        async with SessionCreator() as session:
            db_task = await self._task_repo.update_task_status(
                session=session,
                task_id=task_id,
                status=TaskStatus.CANCELLED.value,
                current_step=f"已取消: {reason}" if reason else "已取消",
            )
            if not db_task:
                return None
            await session.commit()
            return Task.from_db_model(db_task)

    async def delete_task(self, task_id: str) -> bool:
        """删除任务"""
        async with SessionCreator() as session:
            success = await self._task_repo.delete_task(session, task_id)
            if success:
                await session.commit()
            return success

    async def get_statistics(self) -> Dict[str, Any]:
        """获取任务统计"""
        async with SessionCreator() as session:
            return await self._task_repo.get_statistics(session)

    async def count_active_tasks_for_agent(self, agent_id: str) -> int:
        """统计 Agent 的活跃任务数量（规则2：单任务限制）"""
        async with SessionCreator() as session:
            return await self._task_repo.count_active_tasks_for_agent(session, agent_id)

    async def get_stale_tasks(self, timeout_hours: int = 1) -> List[Task]:
        """获取超时的活跃任务（规则1：超时自动失败）"""
        async with SessionCreator() as session:
            db_tasks = await self._task_repo.get_stale_tasks(session, timeout_hours)
            return [Task.from_db_model(t) for t in db_tasks]

    async def mark_task_as_failed(self, task_id: str, reason: str) -> Optional[Task]:
        """标记任务为失败状态"""
        async with SessionCreator() as session:
            db_task = await self._task_repo.get_task(session, task_id)
            if not db_task:
                return None

            db_task.status = TaskStatus.FAILED.value
            db_task.error = {
                "code": "TIMEOUT",
                "message": reason,
                "retry_possible": True,
            }
            db_task.completed_at = datetime.utcnow()
            await session.commit()

            return Task.from_db_model(db_task)

    async def get_source_context(self, source_type: str, source_id: str) -> Dict:
        """获取源对象的上下文信息"""
        async with SessionCreator() as session:
            if source_type == "requirement":
                from opentask.models.requirement.model import Requirement
                source = await session.get(Requirement, source_id)
                if source:
                    return {
                        "source_type": "requirement",
                        "source_id": str(source.id),
                        "source_code": source.code,
                        "source_title": source.title,
                    }
            elif source_type == "issue":
                from opentask.models.issue.model import Issue
                source = await session.get(Issue, source_id)
                if source:
                    return {
                        "source_type": "issue",
                        "source_id": str(source.id),
                        "source_code": source.issue_code,
                        "source_title": source.title,
                    }
            raise ValueError(f"源对象不存在: {source_type}/{source_id}")

    def build_task_description(self, source_context: Dict, comment_content: str, user_description: str) -> str:
        """构建任务描述，包含完整上下文"""
        source_type = source_context["source_type"]
        source_type_zh = "需求" if source_type == "requirement" else "Issue"

        desc = f"## 任务来源\n\n"
        desc += f"- **类型**: {source_type_zh}\n"
        desc += f"- **编号**: {source_context['source_code']}\n"
        desc += f"- **标题**: {source_context['source_title']}\n\n"

        desc += f"## 任务描述\n\n{user_description}\n\n"
        desc += f"## 原始评论\n\n{comment_content}\n\n"
        desc += f"## 创建信息\n\n"
        desc += f"- **创建时间**: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
        desc += f"- **创建方式**: 斜杠命令创建\n"

        return desc

    async def create_task_with_links(
        self,
        title: str,
        description: str,
        link_data: List[str],
        context: Dict,
        created_by: str,
        task_type: str = "manual",
        priority: str = "medium",
        assignee: Optional[str] = None,
        dept_id: Optional[str] = None
    ) -> Task:
        """创建带关联关系的任务

        dept_id: 创建来源的主部门 id 快照（None 表示无归属，行保持 NULL）
        """
        async with SessionCreator() as session:
            # 创建任务
            task_id = str(uuid.uuid4())
            db_task = await self._task_repo.create_task(
                session=session,
                task_id=task_id,
                title=title,
                description=description,
                priority=priority,
                assignee=assignee,
                deadline=None,  # 添加缺失的参数
                metadata={
                    **context,
                    "created_from": "comment",
                    "created_at": datetime.utcnow().isoformat()
                },
                requirements=None,  # 添加缺失的参数
                acceptance_criteria=None,  # 添加缺失的参数
                reward=0,  # 添加缺失的参数
                dept_id=dept_id,  # 部门归属快照
            )

            # 设置 link_data
            db_task.link_data = link_data
            db_task.logs = [{
                "timestamp": datetime.utcnow().isoformat(),
                "message": f"任务从评论创建 by {created_by}",
                "type": "info"
            }]

            await session.commit()
            await session.refresh(db_task)

            return Task.from_db_model(db_task)


# 全局单例
_task_service: Optional[TaskService] = None


def get_task_service() -> TaskService:
    """获取任务服务单例"""
    global _task_service
    if _task_service is None:
        _task_service = TaskService()
    return _task_service


# ========== 💰 钱包服务 ==========

class Wallet:
    """钱包实体（内存中表示）"""

    def __init__(
        self,
        agent_id: str,
        balance: int = 0,
        total_earned: int = 0,
        total_spent: int = 0,
        created_at: Optional[str] = None,
        updated_at: Optional[str] = None,
    ):
        self.agent_id = agent_id
        self.balance = balance
        self.total_earned = total_earned
        self.total_spent = total_spent
        self.created_at = created_at or datetime.utcnow().isoformat()
        self.updated_at = updated_at or datetime.utcnow().isoformat()

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "agent_id": self.agent_id,
            "balance": self.balance,
            "total_earned": self.total_earned,
            "total_spent": self.total_spent,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_db_model(cls, db_wallet) -> "Wallet":
        """从数据库模型创建 Wallet 实体"""
        return cls(
            agent_id=db_wallet.agent_id,
            balance=db_wallet.balance,
            total_earned=db_wallet.total_earned,
            total_spent=db_wallet.total_spent,
            created_at=db_wallet.created_at.isoformat() if db_wallet.created_at else None,
            updated_at=db_wallet.updated_at.isoformat() if db_wallet.updated_at else None,
        )


class Transaction:
    """交易实体（内存中表示）"""

    def __init__(
        self,
        id: str,
        agent_id: str,
        amount: int,
        balance_after: int,
        transaction_type: str,
        description: str,
        related_task_id: Optional[str] = None,
        created_at: Optional[str] = None,
    ):
        self.id = id
        self.agent_id = agent_id
        self.amount = amount
        self.balance_after = balance_after
        self.transaction_type = transaction_type
        self.description = description
        self.related_task_id = related_task_id
        self.created_at = created_at or datetime.utcnow().isoformat()

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "agent_id": self.agent_id,
            "amount": self.amount,
            "balance_after": self.balance_after,
            "transaction_type": self.transaction_type,
            "description": self.description,
            "related_task_id": self.related_task_id,
            "created_at": self.created_at,
        }

    @classmethod
    def from_db_model(cls, db_transaction) -> "Transaction":
        """从数据库模型创建 Transaction 实体"""
        return cls(
            id=db_transaction.id,
            agent_id=db_transaction.agent_id,
            amount=db_transaction.amount,
            balance_after=db_transaction.balance_after,
            transaction_type=db_transaction.transaction_type,
            description=db_transaction.description,
            related_task_id=db_transaction.related_task_id,
            created_at=db_transaction.created_at.isoformat() if db_transaction.created_at else None,
        )


class WalletService:
    """钱包服务（使用数据库）"""

    def __init__(self):
        self._wallet_repo = AgentWalletRepository()

    async def get_or_create_wallet(self, agent_id: str) -> Wallet:
        """获取或创建钱包"""
        async with SessionCreator() as session:
            db_wallet = await self._wallet_repo.get_or_create_wallet(session, agent_id)
            await session.commit()
            return Wallet.from_db_model(db_wallet)

    async def get_wallet(self, agent_id: str) -> Optional[Wallet]:
        """获取钱包"""
        async with SessionCreator() as session:
            db_wallet = await self._wallet_repo.get_wallet(session, agent_id)
            if not db_wallet:
                return None
            return Wallet.from_db_model(db_wallet)

    async def get_all_wallets(self) -> List[Wallet]:
        """获取所有钱包"""
        async with SessionCreator() as session:
            db_wallets = await self._wallet_repo.get_all_wallets(session)
            return [Wallet.from_db_model(w) for w in db_wallets]

    async def add_transaction(
        self,
        agent_id: str,
        amount: int,
        transaction_type: str,
        description: str,
        related_task_id: Optional[str] = None,
    ) -> Transaction:
        """添加交易并更新钱包余额"""
        async with SessionCreator() as session:
            db_transaction = await self._wallet_repo.create_transaction(
                session=session,
                agent_id=agent_id,
                amount=amount,
                transaction_type=transaction_type,
                description=description,
                related_task_id=related_task_id,
            )
            await session.commit()
            return Transaction.from_db_model(db_transaction)

    async def get_transactions(
        self,
        agent_id: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[List[Transaction], int]:
        """获取交易列表"""
        async with SessionCreator() as session:
            db_transactions, total = await self._wallet_repo.get_transactions(
                session=session,
                agent_id=agent_id,
                limit=limit,
                offset=offset,
            )
            transactions = [Transaction.from_db_model(t) for t in db_transactions]
            return transactions, total

    async def get_statistics(self) -> Dict[str, Any]:
        """获取钱包统计"""
        async with SessionCreator() as session:
            return await self._wallet_repo.get_statistics(session)


# 全局单例
_wallet_service: Optional[WalletService] = None


def get_wallet_service() -> WalletService:
    """获取钱包服务单例"""
    global _wallet_service
    if _wallet_service is None:
        _wallet_service = WalletService()
    return _wallet_service
