"""Agent Repository - Agent 数据访问层"""
from datetime import datetime, timedelta
from typing import Optional, List

from sqlalchemy import Select, desc, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from opentask.models.agent import Agent


class AgentRepository:
    """Agent Repository"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(
        self,
        agent_id: str,
        agent_type: str,
        agent_name: str,
        capabilities: Optional[List[str]] = None,
        model: Optional[str] = None,
    ) -> Agent:
        """创建 Agent"""
        agent = Agent(
            agent_id=agent_id,
            agent_type=agent_type,
            agent_name=agent_name,
            capabilities=capabilities,
            model=model,
        )

        self.session.add(agent)
        await self.session.flush()

        return agent

    async def get_by_id(self, agent_id: str) -> Optional[Agent]:
        """根据 ID 获取 Agent"""
        stmt: Select = select(Agent).where(Agent.agent_id == agent_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list(
        self,
        skip: int = 0,
        limit: int = 50,
        agent_type: Optional[str] = None,
        status: Optional[str] = None,
        is_active: Optional[bool] = None,
    ) -> List[Agent]:
        """获取 Agent 列表"""
        conditions = []

        if agent_type:
            conditions.append(Agent.agent_type == agent_type)
        if status:
            conditions.append(Agent.status == status)
        if is_active is not None:
            conditions.append(Agent.is_active == is_active)

        stmt: Select = (
            select(Agent)
            .where(*conditions)
            .order_by(desc(Agent.created_at))
            .offset(skip)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def update_status(
        self,
        agent_id: str,
        status: str,
        previous_status: Optional[str] = None,
    ) -> Optional[Agent]:
        """更新 Agent 状态"""
        agent = await self.get_by_id(agent_id)
        if not agent:
            return None

        agent.status = status
        if previous_status:
            agent.previous_status = previous_status
        agent.updated_at = datetime.utcnow()

        await self.session.flush()
        return agent

    async def update_heartbeat(self, agent_id: str) -> Optional[Agent]:
        """更新心跳时间"""
        agent = await self.get_by_id(agent_id)
        if not agent:
            return None

        agent.last_heartbeat = datetime.utcnow()
        agent.heartbeat_misses = 0
        agent.updated_at = datetime.utcnow()

        await self.session.flush()
        return agent

    async def increment_heartbeat_misses(self, agent_id: str) -> Optional[Agent]:
        """增加心跳丢失次数"""
        agent = await self.get_by_id(agent_id)
        if not agent:
            return None

        agent.heartbeat_misses += 1
        agent.updated_at = datetime.utcnow()

        await self.session.flush()
        return agent

    async def update_task_stats(
        self,
        agent_id: str,
        success: bool = True,
        execution_time: int = 0,
    ) -> Optional[Agent]:
        """更新任务统计"""
        agent = await self.get_by_id(agent_id)
        if not agent:
            return None

        agent.total_tasks_handled += 1
        if success:
            agent.successful_tasks += 1
        else:
            agent.failed_tasks += 1
        agent.total_execution_time += execution_time
        agent.updated_at = datetime.utcnow()

        await self.session.flush()
        return agent

    async def set_current_task(
        self,
        agent_id: str,
        task_id: Optional[str],
    ) -> Optional[Agent]:
        """设置当前任务"""
        agent = await self.get_by_id(agent_id)
        if not agent:
            return None

        agent.current_task_id = task_id
        if task_id:
            agent.current_task_started_at = datetime.utcnow()
        else:
            agent.current_task_started_at = None
        agent.updated_at = datetime.utcnow()

        await self.session.flush()
        return agent

    async def record_error(
        self,
        agent_id: str,
        error_message: str,
    ) -> Optional[Agent]:
        """记录错误"""
        agent = await self.get_by_id(agent_id)
        if not agent:
            return None

        agent.error_count += 1
        agent.last_error = error_message
        agent.last_error_at = datetime.utcnow()
        agent.updated_at = datetime.utcnow()

        await self.session.flush()
        return agent

    async def retire(
        self,
        agent_id: str,
        retired_by: str,
        reason: str,
    ) -> Optional[Agent]:
        """退役 Agent"""
        agent = await self.get_by_id(agent_id)
        if not agent:
            return None

        # 检查是否有正在执行的任务
        if agent.current_task_id:
            raise ValueError(f"Agent {agent_id} has active task, cannot retire")

        agent.status = "retired"
        agent.is_active = False
        agent.retired_at = datetime.utcnow()
        agent.retired_by = retired_by
        agent.retire_reason = reason
        agent.updated_at = datetime.utcnow()

        await self.session.flush()
        return agent

    async def reactivate(self, agent_id: str) -> Optional[Agent]:
        """重新激活 Agent"""
        agent = await self.get_by_id(agent_id)
        if not agent:
            return None

        agent.is_active = True
        agent.updated_at = datetime.utcnow()

        await self.session.flush()
        return agent

    async def get_offline_agents(
        self,
        heartbeat_timeout_seconds: int = 60,
    ) -> List[Agent]:
        """获取心跳超时的 Agent"""
        timeout_threshold = datetime.utcnow() - timedelta(seconds=heartbeat_timeout_seconds)

        stmt: Select = select(Agent).where(
            Agent.last_heartbeat < timeout_threshold,
            Agent.status.in_(["online", "idle", "busy"]),
            Agent.is_active == True,
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
