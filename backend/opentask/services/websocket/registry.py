"""
WebSocket Hub - Agent 注册表

管理已连接的 Agent 信息
"""

import logging
from datetime import datetime
from typing import Dict, Set, Optional, List
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class AgentStatus(Enum):
    """Agent 状态"""
    IDLE = "idle"
    BUSY = "busy"
    OFFLINE = "offline"


@dataclass
class AgentInfo:
    """已注册 Agent 信息"""
    agent_id: str
    name: str
    agent_type: str
    capabilities: List[str] = field(default_factory=list)
    supported_task_types: List[str] = field(default_factory=list)
    max_concurrent_tasks: int = 1
    endpoint: str = ""
    metadata: dict = field(default_factory=dict)
    connected_at: str = field(default_factory=lambda: datetime.now().isoformat())
    last_heartbeat: str = field(default_factory=lambda: datetime.now().isoformat())
    status: AgentStatus = AgentStatus.IDLE
    current_task_count: int = 0
    queued_task_count: int = 0
    websocket = None  # WebSocket 连接对象

    def update_heartbeat(self, status: str = "idle", current_task_count: int = 0, queued_task_count: int = 0):
        """更新心跳信息"""
        self.last_heartbeat = datetime.now().isoformat()
        self.status = AgentStatus(status)
        self.current_task_count = current_task_count
        self.queued_task_count = queued_task_count


class AgentRegistry:
    """Agent 注册表"""

    def __init__(self):
        # agent_id -> AgentInfo
        self._agents: Dict[str, AgentInfo] = {}
        # agent_type -> set of agent_id
        self._by_type: Dict[str, Set[str]] = {}

    def register(self, info: AgentInfo) -> bool:
        """
        注册 Agent

        Args:
            info: Agent 信息

        Returns:
            是否注册成功
        """
        if info.agent_id in self._agents:
            logger.warning(f"Agent {info.agent_id} already registered, updating info")
            # 更新现有 Agent
            old_info = self._agents[info.agent_id]
            # 移除旧的类型索引
            if old_info.agent_type in self._by_type:
                self._by_type[old_info.agent_type].discard(info.agent_id)

        # 注册新 Agent
        self._agents[info.agent_id] = info

        # 建立类型索引
        if info.agent_type not in self._by_type:
            self._by_type[info.agent_type] = set()
        self._by_type[info.agent_type].add(info.agent_id)

        logger.info(f"✅ Agent registered: {info.name} ({info.agent_type}) [id: {info.agent_id}]")
        return True

    def unregister(self, agent_id: str) -> bool:
        """
        注销 Agent

        Args:
            agent_id: Agent ID

        Returns:
            是否成功注销
        """
        if agent_id not in self._agents:
            logger.warning(f"Agent {agent_id} not found in registry")
            return False

        info = self._agents[agent_id]

        # 移除类型索引
        if info.agent_type in self._by_type:
            self._by_type[info.agent_type].discard(agent_id)

        # 移除 Agent
        del self._agents[agent_id]

        logger.info(f"❌ Agent unregistered: {agent_id}")
        return True

    def get(self, agent_id: str) -> Optional[AgentInfo]:
        """获取 Agent 信息"""
        return self._agents.get(agent_id)

    def get_all(self) -> List[AgentInfo]:
        """获取所有 Agent"""
        return list(self._agents.values())

    def get_by_type(self, agent_type: str) -> List[AgentInfo]:
        """按类型获取 Agent"""
        agent_ids = self._by_type.get(agent_type, set())
        return [self._agents[aid] for aid in agent_ids if aid in self._agents]

    def get_idle_by_type(self, agent_type: str) -> List[AgentInfo]:
        """按类型获取空闲 Agent"""
        return [
            agent for agent in self.get_by_type(agent_type)
            if agent.status == AgentStatus.IDLE
        ]

    def update_heartbeat(self, agent_id: str, status: str = "idle",
                        current_task_count: int = 0, queued_task_count: int = 0) -> bool:
        """更新 Agent 心跳"""
        agent = self.get(agent_id)
        if not agent:
            return False

        agent.update_heartbeat(status, current_task_count, queued_task_count)
        return True

    def set_busy(self, agent_id: str) -> bool:
        """设置 Agent 为忙碌状态"""
        agent = self.get(agent_id)
        if not agent:
            return False

        agent.status = AgentStatus.BUSY
        return True

    def set_idle(self, agent_id: str) -> bool:
        """设置 Agent 为空闲状态"""
        agent = self.get(agent_id)
        if not agent:
            return False

        agent.status = AgentStatus.IDLE
        return True

    def count(self) -> int:
        """获取 Agent 总数"""
        return len(self._agents)

    def count_by_type(self, agent_type: str) -> int:
        """获取指定类型的 Agent 数量"""
        return len(self._by_type.get(agent_type, set()))

    def is_registered(self, agent_id: str) -> bool:
        """检查 Agent 是否已注册"""
        return agent_id in self._agents

    def get_status_summary(self) -> dict:
        """获取状态摘要"""
        summary = {
            "total": len(self._agents),
            "by_type": {},
            "by_status": {
                "idle": 0,
                "busy": 0,
                "offline": 0,
            }
        }

        for agent in self._agents.values():
            # 按类型统计
            if agent.agent_type not in summary["by_type"]:
                summary["by_type"][agent.agent_type] = 0
            summary["by_type"][agent.agent_type] += 1

            # 按状态统计
            status_key = agent.status.value
            if status_key in summary["by_status"]:
                summary["by_status"][status_key] += 1

        return summary
