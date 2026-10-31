"""
WebSocket Hub - 配置管理

负责加载和管理 YAML 配置文件
"""

import os
import yaml
import logging
from pathlib import Path
from typing import Any, Optional
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class HubConfig:
    """Hub 主配置"""
    host: str = "localhost"
    port: int = 8765
    log_level: str = "INFO"
    # 认证配置
    auth_enabled: bool = True
    auth_token: str = ""
    auth_allowed_types: list[str] = field(default_factory=lambda: [
        "coding", "review", "design", "research"
    ])


@dataclass
class AgentConfig:
    """Agent 配置"""
    agent_id: str
    name: str
    agent_type: str
    enabled: bool = True
    capabilities: list[str] = field(default_factory=list)
    supported_task_types: list[str] = field(default_factory=list)
    max_concurrent_tasks: int = 1
    config: dict = field(default_factory=dict)


@dataclass
class RoutingConfig:
    """路由配置"""
    default_strategy: str = "round_robin"  # round_robin, least_loaded, random
    type_mappings: dict[str, list[str]] = field(default_factory=dict)


class ConfigManager:
    """配置管理器"""

    def __init__(self, config_dir: Optional[str] = None):
        if config_dir:
            self.config_dir = Path(config_dir)
        else:
            # 默认使用相对于模块的 config 目录
            self.config_dir = Path(__file__).parent.parent.parent / "config"

        self.hub_config: Optional[HubConfig] = None
        self.agents: dict[str, AgentConfig] = {}
        self.routing: Optional[RoutingConfig] = None

    def load(self) -> HubConfig:
        """加载所有配置"""
        self._load_hub_config()
        self._load_agents()
        self._load_routing()

        logger.info(f"Configuration loaded from {self.config_dir}")
        return self.hub_config

    def _load_hub_config(self):
        """加载 Hub 主配置"""
        config_file = self.config_dir / "hub.yaml"

        if not config_file.exists():
            logger.info(f"Hub config not found at {config_file}, using defaults")
            self.hub_config = HubConfig()
            return

        with open(config_file, 'r') as f:
            data = yaml.safe_load(f) or {}

        # 解析认证配置
        auth_data = data.get('auth', {})
        auth_enabled = auth_data.get('enabled', True)
        auth_token = auth_data.get('token', os.environ.get('VIBEKING_AGENT_TOKEN', ''))
        if auth_token.startswith('${') and auth_token.endswith('}'):
            # 处理环境变量引用
            env_var = auth_token[2:-1]
            auth_token = os.environ.get(env_var, '')

        self.hub_config = HubConfig(
            host=data.get('host', 'localhost'),
            port=data.get('port', 8765),
            log_level=data.get('log_level', 'INFO'),
            auth_enabled=auth_enabled,
            auth_token=auth_token,
            auth_allowed_types=auth_data.get('allowed_agent_types', [
                "coding", "review", "design", "research"
            ]),
        )

    def _load_agents(self):
        """加载 Agent 配置"""
        config_file = self.config_dir / "agents.yaml"

        if not config_file.exists():
            logger.info(f"Agents config not found at {config_file}")
            return

        with open(config_file, 'r') as f:
            data = yaml.safe_load(f) or {}

        agents_list = data.get('agents', [])
        for agent_data in agents_list:
            agent = AgentConfig(
                agent_id=agent_data['agent_id'],
                name=agent_data['name'],
                agent_type=agent_data['agent_type'],
                enabled=agent_data.get('enabled', True),
                capabilities=agent_data.get('capabilities', []),
                supported_task_types=agent_data.get('supported_task_types', []),
                max_concurrent_tasks=agent_data.get('max_concurrent_tasks', 1),
                config=agent_data.get('config', {}),
            )
            self.agents[agent.agent_id] = agent

    def _load_routing(self):
        """加载路由配置"""
        config_file = self.config_dir / "routing.yaml"

        if not config_file.exists():
            logger.info(f"Routing config not found at {config_file}, using defaults")
            self.routing = RoutingConfig()
            return

        with open(config_file, 'r') as f:
            data = yaml.safe_load(f) or {}

        routing_data = data.get('routing', {})
        self.routing = RoutingConfig(
            default_strategy=routing_data.get('default_strategy', 'round_robin'),
            type_mappings=routing_data.get('type_mappings', {}),
        )

    def get_agent(self, agent_id: str) -> Optional[AgentConfig]:
        """获取 Agent 配置"""
        return self.agents.get(agent_id)

    def get_agents_by_type(self, agent_type: str) -> list[AgentConfig]:
        """按类型获取 Agent 配置"""
        return [
            agent for agent in self.agents.values()
            if agent.enabled and agent.agent_type == agent_type
        ]

    def get_routing_for_type(self, agent_type: str) -> list[str]:
        """获取指定类型的路由目标 Agent ID"""
        if self.routing and agent_type in self.routing.type_mappings:
            return self.routing.type_mappings[agent_type]
        return []


def load_config(config_dir: Optional[str] = None) -> HubConfig:
    """便捷函数：加载配置"""
    manager = ConfigManager(config_dir)
    return manager.load()
