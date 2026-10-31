"""
Agent Task Repository 单元测试

测试 Repository 层的数据访问逻辑
使用统一的测试配置（tests/conftest.py）
"""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from opentask.models.agent_task import AgentTask, AgentWallet, AgentTransaction
from opentask.repositories.agent_task import AgentTaskRepository, AgentWalletRepository


# 使用统一测试配置中的 fixtures：
# - test_session: 测试数据库会话
# - test_engine: 测试数据库引擎


class TestAgentTaskRepository:
    """Agent Task Repository 测试"""

    @pytest.mark.asyncio
    async def test_create_task(self, test_session):
        """测试创建任务"""
        repo = AgentTaskRepository()

        task = await repo.create_task(
            session=test_session,
            task_id="test_task_001",
            title="测试任务",
            description="这是一个测试任务",
            priority="high",
            assignee="agent-001",
            deadline="2025-12-31T23:59:59Z",
            metadata={"project": "test"},
            requirements=["REQ-001"],
            acceptance_criteria=["完成功能"],
            reward=100,
        )

        assert task is not None
        assert task.task_id == "test_task_001"
        assert task.title == "测试任务"
        assert task.priority == "high"
        assert task.assignee == "agent-001"
        assert task.reward == 100

    @pytest.mark.asyncio
    async def test_get_task(self, test_session):
        """测试获取任务"""
        repo = AgentTaskRepository()

        # 先创建任务
        await repo.create_task(
            session=test_session,
            task_id="test_task_002",
            title="获取测试",
            description="测试获取功能",
            priority="medium",
            assignee="agent-002",
            metadata={},
            requirements=[],
            acceptance_criteria=[],
            reward=0,
        )

        # 获取任务
        task = await repo.get_task(test_session, "test_task_002")

        assert task is not None
        assert task.title == "获取测试"

    @pytest.mark.asyncio
    async def test_get_nonexistent_task(self, test_session):
        """测试获取不存在的任务"""
        repo = AgentTaskRepository()

        task = await repo.get_task(test_session, "nonexistent")

        assert task is None

    @pytest.mark.asyncio
    async def test_list_tasks(self, test_session):
        """测试列出任务"""
        repo = AgentTaskRepository()

        # 创建多个任务
        await repo.create_task(
            session=test_session,
            task_id="test_task_003",
            title="任务1",
            description="描述1",
            priority="high",
            assignee="agent-001",
            metadata={},
            requirements=[],
            acceptance_criteria=[],
            reward=0,
        )

        await repo.create_task(
            session=test_session,
            task_id="test_task_004",
            title="任务2",
            description="描述2",
            priority="low",
            assignee="agent-002",
            metadata={},
            requirements=[],
            acceptance_criteria=[],
            reward=0,
        )

        # 列出所有任务
        tasks = await repo.list_tasks(session=test_session)

        assert len(tasks) == 2

    @pytest.mark.asyncio
    async def test_list_tasks_with_filter(self, test_session):
        """测试过滤任务"""
        repo = AgentTaskRepository()

        # 创建不同状态的任务
        await repo.create_task(
            session=test_session,
            task_id="test_task_005",
            title="任务1",
            description="描述1",
            priority="high",
            assignee="agent-001",
            metadata={},
            requirements=[],
            acceptance_criteria=[],
            reward=0,
        )

        await repo.create_task(
            session=test_session,
            task_id="test_task_006",
            title="任务2",
            description="描述2",
            priority="low",
            assignee="agent-002",
            metadata={},
            requirements=[],
            acceptance_criteria=[],
            reward=0,
        )

        # 更新第一个任务状态
        await repo.update_task_status(
            session=test_session,
            task_id="test_task_005",
            status="in_progress",
            progress_percentage=50,
            current_step="执行中",
        )

        # 过滤进行中的任务
        tasks = await repo.list_tasks(
            session=test_session,
            status="in_progress"
        )

        assert len(tasks) == 1
        assert tasks[0].task_id == "test_task_005"

    @pytest.mark.asyncio
    async def test_update_task_status(self, test_session):
        """测试更新任务状态"""
        repo = AgentTaskRepository()

        # 创建任务
        await repo.create_task(
            session=test_session,
            task_id="test_task_007",
            title="更新测试",
            description="测试更新",
            priority="medium",
            assignee="agent-001",
            metadata={},
            requirements=[],
            acceptance_criteria=[],
            reward=0,
        )

        # 更新任务
        updated_task = await repo.update_task_status(
            session=test_session,
            task_id="test_task_007",
            status="in_progress",
            progress_percentage=75,
            current_step="执行中",
        )

        assert updated_task is not None
        assert updated_task.status == "in_progress"
        assert updated_task.progress_percentage == 75

    @pytest.mark.asyncio
    async def test_delete_task(self, test_session):
        """测试删除任务"""
        repo = AgentTaskRepository()

        # 创建任务
        await repo.create_task(
            session=test_session,
            task_id="test_task_008",
            title="待删除",
            description="将被删除",
            priority="low",
            assignee="agent-003",
            metadata={},
            requirements=[],
            acceptance_criteria=[],
            reward=0,
        )

        # 删除任务
        success = await repo.delete_task(test_session, "test_task_008")

        assert success is True

        # 验证已删除
        task = await repo.get_task(test_session, "test_task_008")
        assert task is None

    @pytest.mark.asyncio
    async def test_count_tasks(self, test_session):
        """测试统计任务数量"""
        repo = AgentTaskRepository()

        # 创建任务
        await repo.create_task(
            session=test_session,
            task_id="test_task_009",
            title="任务1",
            description="描述1",
            priority="high",
            assignee="agent-001",
            metadata={},
            requirements=[],
            acceptance_criteria=[],
            reward=0,
        )

        await repo.create_task(
            session=test_session,
            task_id="test_task_010",
            title="任务2",
            description="描述2",
            priority="medium",
            assignee="agent-001",
            metadata={},
            requirements=[],
            acceptance_criteria=[],
            reward=0,
        )

        # 统计总数
        count = await repo.count_tasks(session=test_session)

        assert count == 2


class TestAgentWalletRepository:
    """Agent Wallet Repository 测试"""

    @pytest.mark.asyncio
    async def test_get_or_create_wallet_new(self, test_session):
        """测试创建新钱包"""
        repo = AgentWalletRepository()

        wallet = await repo.get_or_create_wallet(test_session, "agent-001")

        assert wallet is not None
        assert wallet.agent_id == "agent-001"
        assert wallet.balance == 0
        assert wallet.total_earned == 0
        assert wallet.total_spent == 0

    @pytest.mark.asyncio
    async def test_get_or_create_wallet_existing(self, test_session):
        """测试获取已存在的钱包"""
        repo = AgentWalletRepository()

        # 第一次调用创建
        wallet1 = await repo.get_or_create_wallet(test_session, "agent-002")

        # 第二次调用应返回同一个
        wallet2 = await repo.get_or_create_wallet(test_session, "agent-002")

        assert wallet1.agent_id == wallet2.agent_id
        assert wallet1.agent_id == "agent-002"

    @pytest.mark.asyncio
    async def test_update_balance(self, test_session):
        """测试更新钱包余额"""
        repo = AgentWalletRepository()

        # 创建钱包并充值
        wallet = await repo.update_balance(test_session, "agent-003", 100)

        assert wallet.balance == 100
        assert wallet.total_earned == 100
        assert wallet.total_spent == 0

        # 消费
        wallet = await repo.update_balance(test_session, "agent-003", -30)

        assert wallet.balance == 70
        assert wallet.total_earned == 100
        assert wallet.total_spent == 30

    @pytest.mark.asyncio
    async def test_create_transaction(self, test_session):
        """测试创建交易"""
        repo = AgentWalletRepository()

        # 创建交易
        transaction = await repo.create_transaction(
            session=test_session,
            agent_id="agent-004",
            amount=50,
            transaction_type="task_reward",
            description="任务奖励",
            related_task_id="task_001",
        )

        assert transaction is not None
        assert transaction.agent_id == "agent-004"
        assert transaction.amount == 50
        assert transaction.balance_after == 50
        assert transaction.transaction_type == "task_reward"
        assert transaction.related_task_id == "task_001"

    @pytest.mark.asyncio
    async def test_get_transactions(self, test_session):
        """测试获取交易列表"""
        repo = AgentWalletRepository()

        # 创建多笔交易
        await repo.create_transaction(
            session=test_session,
            agent_id="agent-005",
            amount=100,
            transaction_type="task_reward",
            description="奖励1",
        )

        await repo.create_transaction(
            session=test_session,
            agent_id="agent-005",
            amount=-20,
            transaction_type="manual",
            description="消费",
        )

        # 获取交易列表
        transactions, total = await repo.get_transactions(
            session=test_session,
            agent_id="agent-005",
            limit=10,
            offset=0,
        )

        assert len(transactions) == 2
        assert total == 2

    @pytest.mark.asyncio
    async def test_get_statistics(self, test_session):
        """测试获取钱包统计"""
        repo = AgentWalletRepository()

        # 创建多个钱包和交易
        await repo.update_balance(test_session, "agent-006", 100)
        await repo.update_balance(test_session, "agent-007", 200)
        await repo.create_transaction(
            session=test_session,
            agent_id="agent-006",
            amount=50,
            transaction_type="task_reward",
            description="奖励",
        )

        # 获取统计
        stats = await repo.get_statistics(test_session)

        assert stats["total_balance"] == 300
        assert stats["total_earned"] == 300
        assert stats["transaction_count"] == 1
        assert stats["active_wallets"] == 2
