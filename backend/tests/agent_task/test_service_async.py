"""
Agent Task Service 集成测试

测试 Service 层的业务逻辑
使用统一的测试配置（tests/conftest.py）
"""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from opentask.services.agent_task.service import (
    TaskService,
    Task,
    TaskPriority,
    TaskStatus,
)
from opentask.models.agent_task import AgentTask, AgentWallet, AgentTransaction


# 使用统一测试配置中的 fixtures：
# - test_session: 测试数据库会话
# - test_engine: 测试数据库引擎


class TestTaskServiceAsync:
    """TaskService 异步测试"""

    @pytest.mark.asyncio
    async def test_create_task(self, test_session):
        """测试创建任务"""
        service = TaskService()

        task = await service.create_task(
            title="异步测试任务",
            description="测试异步创建",
            priority=TaskPriority.HIGH,
            assignee="agent-001",
            deadline="2025-12-31T23:59:59Z",
            metadata={"project": "test"},
            requirements=["REQ-001"],
            acceptance_criteria=["完成"],
            reward=100,
        )

        assert task is not None
        assert task.title == "异步测试任务"
        assert task.priority == TaskPriority.HIGH
        assert task.task_id.startswith("task_")

    @pytest.mark.asyncio
    async def test_get_task(self, test_session):
        """测试获取任务"""
        service = TaskService()

        # 创建任务
        created_task = await service.create_task(
            title="获取测试",
            description="测试获取",
            priority=TaskPriority.MEDIUM,
            assignee="agent-002",
        )

        # 获取任务
        task = await service.get_task(created_task.task_id)

        assert task is not None
        assert task.title == "获取测试"

    @pytest.mark.asyncio
    async def test_list_tasks(self, test_session):
        """测试列出任务"""
        service = TaskService()

        # 创建多个任务
        await service.create_task("任务1", "描述1", TaskPriority.HIGH, "agent-001")
        await service.create_task("任务2", "描述2", TaskPriority.LOW, "agent-002")
        await service.create_task("任务3", "描述3", TaskPriority.MEDIUM, "agent-003")

        # 列出任务
        tasks = await service.list_tasks()

        assert len(tasks) == 3

    @pytest.mark.asyncio
    async def test_update_task_status(self, test_session):
        """测试更新任务状态"""
        service = TaskService()

        # 创建任务
        task = await service.create_task(
            title="更新测试",
            description="测试更新",
            priority=TaskPriority.MEDIUM,
            assignee="agent-001",
        )

        # 更新任务
        updated_task = await service.update_task_status(
            task_id=task.task_id,
            status=TaskStatus.IN_PROGRESS,
            progress_percentage=50,
            current_step="执行中",
        )

        assert updated_task is not None
        assert updated_task.status == TaskStatus.IN_PROGRESS
        assert updated_task.progress_percentage == 50

    @pytest.mark.asyncio
    async def test_complete_task(self, test_session):
        """测试完成任务"""
        service = TaskService()

        # 创建任务
        task = await service.create_task(
            title="完成测试",
            description="测试完成",
            priority=TaskPriority.HIGH,
            assignee="agent-001",
        )

        # 完成任务
        result = {"output": "success", "files": 5}
        completed_task = await service.complete_task(
            task_id=task.task_id,
            result=result,
            execution_time_ms=1500,
        )

        assert completed_task is not None
        assert completed_task.status == TaskStatus.COMPLETED
        assert completed_task.progress_percentage == 100
        assert completed_task.result == result
        assert completed_task.execution_time_ms == 1500

    @pytest.mark.asyncio
    async def test_cancel_task(self, test_session):
        """测试取消任务"""
        service = TaskService()

        # 创建任务
        task = await service.create_task(
            title="取消测试",
            description="测试取消",
            priority=TaskPriority.MEDIUM,
            assignee="agent-001",
        )

        # 取消任务
        cancelled_task = await service.cancel_task(task.task_id, "测试取消")

        assert cancelled_task is not None
        assert cancelled_task.status == TaskStatus.CANCELLED

    @pytest.mark.asyncio
    async def test_delete_task(self, test_session):
        """测试删除任务"""
        service = TaskService()

        # 创建任务
        task = await service.create_task(
            title="删除测试",
            description="测试删除",
            priority=TaskPriority.LOW,
            assignee="agent-003",
        )

        # 删除任务
        success = await service.delete_task(task.task_id)

        assert success is True

        # 验证已删除
        deleted_task = await service.get_task(task.task_id)
        assert deleted_task is None

    @pytest.mark.asyncio
    async def test_get_statistics(self, test_session):
        """测试获取统计信息"""
        service = TaskService()

        # 创建任务
        await service.create_task("任务1", "描述1", TaskPriority.URGENT, "agent-001")
        await service.create_task("任务2", "描述2", TaskPriority.HIGH, "agent-002")

        # 更新任务状态
        tasks = await service.list_tasks()
        if len(tasks) > 0:
            await service.update_task_status(
                tasks[0].task_id,
                TaskStatus.IN_PROGRESS,
            )

        # 获取统计
        stats = await service.get_statistics()

        assert stats["total"] == 2
        assert "by_status" in stats
        assert "by_priority" in stats


class TestWalletServiceAsync:
    """WalletService 异步测试"""

    @pytest.mark.asyncio
    async def test_get_or_create_wallet(self, test_session):
        """测试获取或创建钱包"""
        from opentask.services.agent_task.service import WalletService

        service = WalletService()

        # 第一次调用创建
        wallet1 = await service.get_or_create_wallet("agent-001")

        assert wallet1 is not None
        assert wallet1.balance == 0

        # 第二次调用应返回已存在的
        wallet2 = await service.get_or_create_wallet("agent-001")

        assert wallet2.agent_id == wallet1.agent_id

    @pytest.mark.asyncio
    async def test_add_transaction(self, test_session):
        """测试添加交易"""
        from opentask.services.agent_task.service import WalletService

        service = WalletService()

        # 添加交易（充值）
        transaction = await service.add_transaction(
            agent_id="agent-002",
            amount=100,
            transaction_type="task_reward",
            description="任务奖励",
            related_task_id="task_001",
        )

        assert transaction is not None
        assert transaction.amount == 100
        assert transaction.balance_after == 100

    @pytest.mark.asyncio
    async def test_get_transactions(self, test_session):
        """测试获取交易列表"""
        from opentask.services.agent_task.service import WalletService

        service = WalletService()

        # 添加交易
        await service.add_transaction(
            agent_id="agent-003",
            amount=100,
            transaction_type="task_reward",
            description="奖励1",
        )

        await service.add_transaction(
            agent_id="agent-003",
            amount=-20,
            transaction_type="manual",
            description="消费",
        )

        # 获取交易列表
        transactions, total = await service.get_transactions(
            agent_id="agent-003",
            limit=10,
            offset=0,
        )

        assert len(transactions) == 2
        assert total == 2
