"""
WebSocket Hub - 认证模块

负责 Agent 连接时的身份验证
"""

import os
import logging
from typing import Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class AuthConfig:
    """认证配置"""
    enabled: bool = True
    token: str = ""
    allowed_agent_types: list[str] = None

    def __post_init__(self):
        if self.allowed_agent_types is None:
            self.allowed_agent_types = ["coding", "review", "design", "research"]


class AuthManager:
    """认证管理器"""

    def __init__(self, config: AuthConfig):
        self.config = config
        self._validate_config()

    def _validate_config(self):
        """验证配置"""
        if self.config.enabled and not self.config.token:
            # 尝试从环境变量获取
            token = os.environ.get("OPENTASK_AGENT_TOKEN")
            if token:
                self.config.token = token
            else:
                logger.warning("Agent authentication is enabled but no token configured")

    def authenticate(
        self,
        token: Optional[str],
        agent_id: str,
        agent_type: str
    ) -> tuple[bool, Optional[str]]:
        """
        验证 Agent 身份

        Args:
            token: 客户端提供的 token
            agent_id: Agent ID
            agent_type: Agent 类型

        Returns:
            (是否通过, 错误消息)
        """
        if not self.config.enabled:
            return True, None

        # 检查 token
        if not token:
            return False, "Missing authentication token"

        if token != self.config.token:
            logger.warning(f"Invalid token for agent {agent_id}")
            return False, "Invalid authentication token"

        # 检查 agent_type
        if agent_type not in self.config.allowed_agent_types:
            logger.warning(f"Agent type '{agent_type}' not allowed for agent {agent_id}")
            return False, f"Agent type '{agent_type}' not allowed"

        return True, None

    def generate_token(self) -> str:
        """生成新的 Agent token"""
        import secrets
        return secrets.token_urlsafe(32)
