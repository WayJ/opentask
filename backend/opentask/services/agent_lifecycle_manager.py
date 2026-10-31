"""Agent 生命周期管理器"""
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from opentask.models.agent import Agent
from opentask.repositories.agent_repository import AgentRepository


class AgentLifecycleManager:
    """Agent 生命周期管理器"""

    # Agent 状态定义
    STATUS_REGISTERED = "registered"
    STATUS_ONLINE = "online"
    STATUS_IDLE = "idle"
    STATUS_BUSY = "busy"
    STATUS_OFFLINE = "offline"
    STATUS_RETIRED = "retired"
    STATUS_ERROR = "error"

    def __init__(self, session: AsyncSession):
        self.session = session
        self.agent_repo = AgentRepository(session)
        self.heartbeat_timeout = 60  # 心跳超时时间（秒）
        self.max_heartbeat_misses = 2  # 最大心跳丢失次数

    async def handle_agent_registered(
        self,
        agent_id: str,
        agent_type: str,
        agent_name: str,
        capabilities: Optional[list] = None,
        model: Optional[str] = None,
    ) -> Agent:
        """处理 Agent 注册"""
        # 检查 Agent 是否已存在
        existing_agent = await self.agent_repo.get_by_id(agent_id)

        if existing_agent:
            # 如果已存在且已退役，重新激活
            if existing_agent.status == self.STATUS_RETIRED:
                existing_agent = await self.agent_repo.reactivate(agent_id)
                existing_agent.status = self.STATUS_REGISTERED
                existing_agent.agent_type = agent_type
                existing_agent.agent_name = agent_name
                existing_agent.capabilities = capabilities
                existing_agent.model = model
                existing_agent.connected_at = datetime.utcnow()
                await self.session.flush()
                return existing_agent

            # 更新连接信息
            existing_agent.connected_at = datetime.utcnow()
            existing_agent.agent_name = agent_name
            existing_agent.capabilities = capabilities
            existing_agent.model = model
            await self.session.flush()
            return existing_agent

        # 创建新 Agent
        agent = await self.agent_repo.create(
            agent_id=agent_id,
            agent_type=agent_type,
            agent_name=agent_name,
            capabilities=capabilities,
            model=model,
        )
        agent.status = self.STATUS_REGISTERED
        agent.connected_at = datetime.utcnow()
        await self.session.flush()

        return agent

    async def handle_heartbeat(self, agent_id: str) -> Agent:
        """处理心跳"""
        agent = await self.agent_repo.get_by_id(agent_id)
        if not agent:
            raise ValueError(f"Agent {agent_id} not found")

        # 更新心跳时间
        agent = await self.agent_repo.update_heartbeat(agent_id)

        # 状态转换逻辑
        if agent.status == self.STATUS_OFFLINE:
            # 从离线恢复
            await self._transition_to(agent, self.STATUS_ONLINE)
        elif agent.status == self.STATUS_ONLINE and not agent.current_task_id:
            # 空闲状态
            await self._transition_to(agent, self.STATUS_IDLE)

        return agent

    async def handle_task_start(self, agent_id: str, task_id: str) -> Agent:
        """处理任务开始"""
        agent = await self.agent_repo.get_by_id(agent_id)
        if not agent:
            raise ValueError(f"Agent {agent_id} not found")

        # 设置当前任务
        agent = await self.agent_repo.set_current_task(agent_id, task_id)

        # 转换到忙碌状态
        await self._transition_to(agent, self.STATUS_BUSY)

        return agent

    async def handle_task_complete(
        self,
        agent_id: str,
        success: bool = True,
        execution_time: int = 0,
    ) -> Agent:
        """处理任务完成"""
        agent = await self.agent_repo.get_by_id(agent_id)
        if not agent:
            raise ValueError(f"Agent {agent_id} not found")

        # 清除当前任务
        agent = await self.agent_repo.set_current_task(agent_id, None)

        # 更新统计
        await self.agent_repo.update_task_stats(
            agent_id,
            success=success,
            execution_time=execution_time,
        )

        # 转换到空闲状态
        await self._transition_to(agent, self.STATUS_IDLE)

        return agent

    async def handle_agent_disconnect(self, agent_id: str) -> Agent:
        """处理 Agent 断开连接"""
        agent = await self.agent_repo.get_by_id(agent_id)
        if not agent:
            raise ValueError(f"Agent {agent_id} not found")

        agent.disconnected_at = datetime.utcnow()
        await self.session.flush()

        return agent

    async def check_heartbeat_timeouts(self) -> list[Agent]:
        """检查心跳超时（定时任务调用）"""
        timeout_agents = await self.agent_repo.get_offline_agents(self.heartbeat_timeout)

        for agent in timeout_agents:
            # 增加心跳丢失计数
            agent.heartbeat_misses += 1

            if agent.heartbeat_misses >= self.max_heartbeat_misses:
                # 标记为离线
                await self._transition_to(agent, self.STATUS_OFFLINE)

                # 如果正在处理任务，记录错误
                if agent.current_task_id:
                    await self.agent_repo.record_error(
                        agent.agent_id,
                        f"Heartbeat timeout while processing task {agent.current_task_id}",
                    )

        await self.session.flush()
        return timeout_agents

    async def retire_agent(
        self,
        agent_id: str,
        retired_by: str,
        reason: str,
    ) -> Agent:
        """退役 Agent"""
        agent = await self.agent_repo.get_by_id(agent_id)
        if not agent:
            raise ValueError(f"Agent {agent_id} not found")

        # 检查是否有正在执行的任务
        if agent.current_task_id:
            raise ValueError(
                f"Agent {agent_id} has active task {agent.current_task_id}, cannot retire"
            )

        # 执行退役
        agent = await self.agent_repo.retire(agent_id, retired_by, reason)
        await self._transition_to(agent, self.STATUS_RETIRED)

        return agent

    async def _transition_to(
        self,
        agent: Agent,
        new_status: str,
    ) -> None:
        """内部状态转换方法"""
        old_status = agent.status

        if old_status == new_status:
            return

        # 记录状态变更
        # TODO: 这里可以记录到活动日志（如果有的话）

        # 更新状态
        agent.previous_status = old_status
        agent.status = new_status
        agent.updated_at = datetime.utcnow()

        # 状态特定的处理
        if new_status == self.STATUS_BUSY:
            # 开始处理任务（已在 handle_task_start 中设置 current_task）
            pass
        elif old_status == self.STATUS_BUSY and new_status == self.STATUS_IDLE:
            # 从忙碌恢复到空闲（已在 handle_task_complete 中清除 current_task）
            pass

        await self.session.flush()
