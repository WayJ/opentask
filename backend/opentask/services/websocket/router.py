"""
WebSocket Hub - 消息路由器

负责消息的路由和转发
"""

import logging
from typing import Dict, Set, List, Tuple, Optional, Any
from dataclasses import dataclass
from enum import Enum

from .registry import AgentRegistry, AgentInfo

logger = logging.getLogger(__name__)


class ClientType(Enum):
    """客户端类型"""
    FRONTEND = "frontend"
    BACKEND = "backend"
    AGENT = "agent"
    UNKNOWN = "unknown"


@dataclass
class RouteRule:
    """路由规则"""
    message_pattern: str  # 消息类型模式，支持通配符 *
    sender_types: Set[ClientType]
    recipient_types: Set[ClientType]


class MessageRouter:
    """消息路由器"""

    def __init__(self, registry: AgentRegistry):
        self.registry = registry

        # 客户端连接管理
        self.clients: Dict[ClientType, Set[Any]] = {
            ClientType.FRONTEND: set(),
            ClientType.BACKEND: set(),
            ClientType.AGENT: set(),
        }

        # 默认路由规则
        self.route_rules: List[RouteRule] = [
            # 任务提交 -> frontend/backend -> agent
            RouteRule(
                message_pattern="task:submit",
                sender_types={ClientType.FRONTEND, ClientType.BACKEND},
                recipient_types={ClientType.AGENT},
            ),
            # 任务进度 -> agent -> frontend/backend
            RouteRule(
                message_pattern="task:progress",
                sender_types={ClientType.AGENT},
                recipient_types={ClientType.FRONTEND, ClientType.BACKEND},
            ),
            # 任务完成 -> agent -> frontend/backend
            RouteRule(
                message_pattern="task:complete",
                sender_types={ClientType.AGENT},
                recipient_types={ClientType.FRONTEND, ClientType.BACKEND},
            ),
            # 任务失败 -> agent -> frontend/backend
            RouteRule(
                message_pattern="task:fail",
                sender_types={ClientType.AGENT},
                recipient_types={ClientType.FRONTEND, ClientType.BACKEND},
            ),
            # 任务取消/暂停/恢复 -> frontend/backend -> agent
            RouteRule(
                message_pattern="task:cancel",
                sender_types={ClientType.FRONTEND, ClientType.BACKEND},
                recipient_types={ClientType.AGENT},
            ),
            RouteRule(
                message_pattern="task:pause",
                sender_types={ClientType.FRONTEND, ClientType.BACKEND},
                recipient_types={ClientType.AGENT},
            ),
            RouteRule(
                message_pattern="task:resume",
                sender_types={ClientType.FRONTEND, ClientType.BACKEND},
                recipient_types={ClientType.AGENT},
            ),
            # Agent 注册 -> agent -> 广播给 frontend/backend
            RouteRule(
                message_pattern="agent:register",
                sender_types={ClientType.AGENT},
                recipient_types={ClientType.FRONTEND, ClientType.BACKEND},
            ),
            # Agent 心跳 -> agent -> 广播给 frontend/backend
            RouteRule(
                message_pattern="agent:heartbeat",
                sender_types={ClientType.AGENT},
                recipient_types={ClientType.FRONTEND, ClientType.BACKEND},
            ),
            # Agent 状态变更 -> agent -> 广播
            RouteRule(
                message_pattern="agent:status",
                sender_types={ClientType.AGENT},
                recipient_types={ClientType.FRONTEND, ClientType.BACKEND},
            ),
            # 任务查询 -> frontend/backend -> agent
            RouteRule(
                message_pattern="task:query",
                sender_types={ClientType.FRONTEND, ClientType.BACKEND},
                recipient_types={ClientType.AGENT},
            ),
            # 任务响应 -> agent -> frontend/backend
            RouteRule(
                message_pattern="task:response",
                sender_types={ClientType.AGENT},
                recipient_types={ClientType.FRONTEND, ClientType.BACKEND},
            ),
            # 系统消息确认 -> 任意 -> 任意
            RouteRule(
                message_pattern="system:ack",
                sender_types={ClientType.FRONTEND, ClientType.BACKEND, ClientType.AGENT},
                recipient_types={ClientType.FRONTEND, ClientType.BACKEND, ClientType.AGENT},
            ),
        ]

    def register_client(self, client: Any, client_type: ClientType):
        """注册客户端"""
        self.clients[client_type].add(client)
        logger.debug(f"Client registered: {client_type}")

    def unregister_client(self, client: Any, client_type: ClientType):
        """注销客户端"""
        self.clients[client_type].discard(client)
        logger.debug(f"Client unregistered: {client_type}")

    def get_clients(self, client_type: ClientType) -> Set[Any]:
        """获取指定类型的客户端"""
        return self.clients.get(client_type, set())

    def route_message(self, message: dict, sender_type: ClientType) -> List[Tuple[Any, dict]]:
        """
        路由消息

        Args:
            message: 消息内容
            sender_type: 发送方类型

        Returns:
            [(接收方客户端, 转发消息), ...]
        """
        msg_type = message.get("type", "")
        recipient = message.get("recipient", "")
        payload = message.get("payload", {})

        recipients = []

        # 广播模式
        if recipient == "broadcast":
            for ct in ClientType:
                if ct != sender_type:
                    for client in self.clients[ct]:
                        recipients.append((client, message))
            return recipients

        # 精确指定 Agent ID (格式: agent:xxx)
        if recipient.startswith("agent:"):
            target_agent_id = recipient[6:]  # 去掉 "agent:" 前缀
            for client in self.clients[ClientType.AGENT]:
                # 需要从 WebSocket 对象获取 agent_id
                if hasattr(client, 'agent_id') and client.agent_id == target_agent_id:
                    recipients.append((client, message))
                    return recipients
            # 未找到目标 Agent
            logger.warning(f"Target agent not found: {target_agent_id}")
            return recipients

        # 按 Agent 类型路由 (targetAgent)
        target_agent = payload.get("targetAgent", "")
        if target_agent:
            agents = self.registry.get_by_type(target_agent)
            if agents:
                # 简单的负载均衡：选择最空闲的
                idle_agents = [a for a in agents if a.status.value == "idle"]
                if idle_agents:
                    selected = min(idle_agents, key=lambda a: a.current_task_count)
                else:
                    # 如果没有空闲的，选择负载最低的
                    selected = min(agents, key=lambda a: a.current_task_count)

                # 找到对应的 WebSocket 客户端
                for client in self.clients[ClientType.AGENT]:
                    if hasattr(client, 'agent_id') and client.agent_id == selected.agent_id:
                        recipients.append((client, message))
                        return recipients

            # 没有找到对应类型的 Agent
            logger.warning(f"No agent found for type: {target_agent}")

        # 默认：广播给所有 frontend/backend
        for client in self.clients[ClientType.FRONTEND]:
            recipients.append((client, message))
        for client in self.clients[ClientType.BACKEND]:
            recipients.append((client, message))

        return recipients

    def broadcast_to_type(self, message: dict, target_types: Set[ClientType]):
        """广播消息给指定类型的所有客户端"""
        for target_type in target_types:
            for client in self.clients[target_type]:
                yield client, message
