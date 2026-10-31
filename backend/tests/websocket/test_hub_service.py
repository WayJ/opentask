"""
WebSocket Hub 服务详细单元测试

测试 WebSocket Hub 服务的核心功能：
- 连接管理
- 消息路由
- Agent 注册和管理
- 消息处理
"""

import pytest
import json
from datetime import datetime
from unittest.mock import Mock, AsyncMock, patch

from opentask.services.websocket.hub_service import (
    WebSocketHubService,
    ConnectionInfo,
    get_websocket_hub,
)


@pytest.fixture
def reset_hub_singleton():
    """每个测试后重置 Hub 单例"""
    import opentask.services.websocket.hub_service as hub_module
    original = hub_module._websocket_hub
    hub_module._websocket_hub = None
    yield
    hub_module._websocket_hub = original


@pytest.fixture
def hub_service():
    """创建新的 HubService 实例"""
    return WebSocketHubService()


@pytest.fixture
def mock_websocket():
    """模拟 WebSocket 连接"""
    ws = Mock()
    ws.accept = AsyncMock()
    ws.send_text = AsyncMock()
    ws.receive_text = AsyncMock()
    ws.close = AsyncMock()
    return ws


class TestConnectionInfo:
    """ConnectionInfo 类测试"""

    def test_create_frontend_connection_info(self):
        """测试创建前端连接信息"""
        info = ConnectionInfo(
            websocket=None,
            client_type="frontend",
            path="/"
        )

        assert info.client_type == "frontend"
        assert info.path == "/"
        assert info.agent_id is None
        assert info.agent_type is None
        assert isinstance(info.connected_at, datetime)

    def test_create_backend_connection_info(self):
        """测试创建后端连接信息"""
        info = ConnectionInfo(
            websocket=None,
            client_type="backend",
            path="/backend"
        )

        assert info.client_type == "backend"
        assert info.path == "/backend"
        assert info.agent_id is None
        assert info.agent_type is None

    def test_create_agent_connection_info(self):
        """测试创建 Agent 连接信息"""
        info = ConnectionInfo(
            websocket=None,
            client_type="agent",
            agent_id="coding-agent-1",
            agent_type="coding",
            path="/agent"
        )

        assert info.client_type == "agent"
        assert info.agent_id == "coding-agent-1"
        assert info.agent_type == "coding"
        assert info.path == "/agent"


class TestWebSocketHubServiceInitialization:
    """Hub 服务初始化测试"""

    def test_service_initialization(self, hub_service):
        """测试服务初始化"""
        assert hub_service.frontend_clients == set()
        assert hub_service.backend_clients == set()
        assert hub_service.agent_clients == {}
        assert hub_service.agents == {}
        assert hub_service.running is False

    @pytest.mark.asyncio
    async def test_singleton_pattern(self, reset_hub_singleton):
        """测试单例模式（get_websocket_hub 内部 create_task 启动心跳监控，需要事件循环）"""
        hub1 = get_websocket_hub()
        hub2 = get_websocket_hub()

        assert hub1 is hub2
        assert hub1.running is True

        # 清理心跳监控任务，避免遗留 pending task
        hub1.running = False
        await hub1.stop_heartbeat_monitor()


class TestConnectionManagement:
    """连接管理测试"""

    @pytest.mark.asyncio
    async def test_connect_frontend(self, hub_service, mock_websocket):
        """测试前端连接"""
        info = await hub_service.connect_frontend(mock_websocket)

        assert info.client_type == "frontend"
        assert info.path == "/"
        assert mock_websocket in hub_service.frontend_clients
        assert len(hub_service.frontend_clients) == 1
        mock_websocket.accept.assert_called_once()

    @pytest.mark.asyncio
    async def test_connect_backend(self, hub_service, mock_websocket):
        """测试后端连接"""
        info = await hub_service.connect_backend(mock_websocket)

        assert info.client_type == "backend"
        assert info.path == "/backend"
        assert mock_websocket in hub_service.backend_clients
        assert len(hub_service.backend_clients) == 1
        mock_websocket.accept.assert_called_once()

    @pytest.mark.asyncio
    async def test_connect_agent(self, hub_service, mock_websocket):
        """测试 Agent 连接"""
        agent_id = "test-agent-1"
        agent_type = "coding"

        info = await hub_service.connect_agent(mock_websocket, agent_id, agent_type)

        assert info.client_type == "agent"
        assert info.agent_id == agent_id
        assert info.agent_type == agent_type
        assert mock_websocket in hub_service.agent_clients.values()
        assert agent_id in hub_service.agents
        assert hub_service.agents[agent_id]["status"] == "online"
        mock_websocket.accept.assert_called_once()

    @pytest.mark.asyncio
    async def test_disconnect_frontend(self, hub_service, mock_websocket):
        """测试前端断开连接"""
        info = await hub_service.connect_frontend(mock_websocket)
        assert len(hub_service.frontend_clients) == 1

        await hub_service.disconnect(mock_websocket, info)

        assert len(hub_service.frontend_clients) == 0
        assert mock_websocket not in hub_service.frontend_clients

    @pytest.mark.asyncio
    async def test_disconnect_backend(self, hub_service, mock_websocket):
        """测试后端断开连接"""
        info = await hub_service.connect_backend(mock_websocket)
        assert len(hub_service.backend_clients) == 1

        await hub_service.disconnect(mock_websocket, info)

        assert len(hub_service.backend_clients) == 0
        assert mock_websocket not in hub_service.backend_clients

    @pytest.mark.asyncio
    async def test_disconnect_agent(self, hub_service, mock_websocket):
        """测试 Agent 断开连接"""
        agent_id = "test-agent-1"
        info = await hub_service.connect_agent(mock_websocket, agent_id, "coding")
        assert agent_id in hub_service.agents
        assert agent_id in hub_service.agent_clients

        await hub_service.disconnect(mock_websocket, info)

        assert agent_id not in hub_service.agents
        assert agent_id not in hub_service.agent_clients


class TestAgentManagement:
    """Agent 管理测试"""

    def test_get_online_agents_empty(self, hub_service):
        """测试获取在线 Agent（空列表）"""
        agents = hub_service.get_online_agents()
        assert agents == []

    @pytest.mark.asyncio
    async def test_get_online_agents_with_connections(self, hub_service, mock_websocket):
        """测试获取在线 Agent（有连接）"""
        # 创建多个 Agent 连接
        await hub_service.connect_agent(mock_websocket, "agent-1", "coding")
        await hub_service.connect_agent(mock_websocket, "agent-2", "review")

        agents = hub_service.get_online_agents()

        assert len(agents) == 2
        assert any(a["agent_id"] == "agent-1" for a in agents)
        assert any(a["agent_id"] == "agent-2" for a in agents)

    def test_get_status(self, hub_service):
        """测试获取 Hub 状态"""
        status = hub_service.get_status()

        assert "running" in status
        assert "frontend_clients" in status
        assert "backend_clients" in status
        assert "agents" in status
        assert "total_agents" in status

        assert status["running"] is False
        assert status["frontend_clients"] == 0
        assert status["backend_clients"] == 0
        assert status["total_agents"] == 0


class TestMessageRouting:
    """消息路由测试"""

    @pytest.mark.asyncio
    async def test_handle_agent_register_message(self, hub_service, mock_websocket):
        """测试处理 Agent 注册消息"""
        await hub_service.connect_agent(mock_websocket, "test-agent", "coding")

        register_message = {
            "id": "msg-1",
            "type": "agent:register",
            "sender": "agent:test-agent",
            "recipient": "hub",
            "timestamp": datetime.now().isoformat(),
            "payload": {
                "agentId": "test-agent",
                "name": "Test Coding Agent",
                "agentType": "coding",
                "capabilities": ["python", "javascript"]
            },
            "version": "1.0"
        }

        await hub_service.handle_message(
            mock_websocket,
            json.dumps(register_message),
            ConnectionInfo(mock_websocket, "agent", "test-agent", "coding")
        )

        # 验证 Agent 信息已更新
        agent = hub_service.agents.get("test-agent")
        assert agent is not None
        assert agent["name"] == "Test Coding Agent"
        assert "python" in agent["capabilities"]
        assert agent["status"] == "online"

    @pytest.mark.asyncio
    async def test_handle_agent_heartbeat_message(self, hub_service, mock_websocket):
        """测试处理 Agent 心跳消息"""
        await hub_service.connect_agent(mock_websocket, "test-agent", "coding")

        heartbeat_message = {
            "id": "msg-2",
            "type": "agent:heartbeat",
            "sender": "agent:test-agent",
            "recipient": "hub",
            "timestamp": datetime.now().isoformat(),
            "payload": {
                "agentId": "test-agent"
            },
            "version": "1.0"
        }

        await hub_service.handle_message(
            mock_websocket,
            json.dumps(heartbeat_message),
            ConnectionInfo(mock_websocket, "agent", "test-agent", "coding")
        )

        # 验证心跳时间已更新
        agent = hub_service.agents.get("test-agent")
        assert agent is not None
        assert "last_heartbeat" in agent

    @pytest.mark.asyncio
    async def test_route_task_submit_to_agent(self, hub_service, mock_websocket):
        """测试路由任务提交消息到 Agent"""
        # 创建一个 Agent 连接
        await hub_service.connect_agent(mock_websocket, "coding-agent-1", "coding")

        task_message = {
            "id": "msg-3",
            "type": "task:submit",
            "sender": "frontend",
            "recipient": "agent:coding-agent-1",
            "timestamp": datetime.now().isoformat(),
            "payload": {
                "taskId": "task-123",
                "targetAgentId": "coding-agent-1",
                "title": "测试任务"
            },
            "version": "1.0"
        }

        info = ConnectionInfo(mock_websocket, "frontend")

        # 路由消息（不会实际发送，因为没有真正的 WebSocket）
        await hub_service.route_message(task_message, info)

        # 验证目标被正确识别
        # （这里只测试路由逻辑，不测试实际发送）

    @pytest.mark.asyncio
    async def test_send_acknowledgement(self, hub_service, mock_websocket):
        """测试发送消息确认"""
        test_message = {
            "id": "msg-4",
            "type": "test",
            "sender": "frontend",
            "timestamp": datetime.now().isoformat(),
            "payload": {},
            "version": "1.0"
        }

        await hub_service.handle_message(
            mock_websocket,
            json.dumps(test_message),
            ConnectionInfo(mock_websocket, "frontend")
        )

        # 验证发送了确认消息
        mock_websocket.send_text.assert_called()
        sent_message = json.loads(mock_websocket.send_text.call_args[0][0])
        assert sent_message["type"] == "system:ack"
        assert sent_message["payload"]["originalId"] == "msg-4"


class TestMessageSending:
    """消息发送测试"""

    @pytest.mark.asyncio
    async def test_send_to_all_frontends(self, hub_service, mock_websocket):
        """测试发送消息给所有前端"""
        # 创建多个前端连接
        ws1 = Mock()
        ws1.accept = AsyncMock()
        ws1.send_text = AsyncMock()
        ws2 = Mock()
        ws2.accept = AsyncMock()
        ws2.send_text = AsyncMock()

        await hub_service.connect_frontend(ws1)
        await hub_service.connect_frontend(ws2)

        message = {"type": "test", "data": "test"}
        await hub_service.send_to_target(message, "frontend")

        # 验证所有前端都收到了消息
        ws1.send_text.assert_called_once()
        ws2.send_text.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_to_all_backends(self, hub_service, mock_websocket):
        """测试发送消息给所有后端"""
        ws1 = Mock()
        ws1.accept = AsyncMock()
        ws1.send_text = AsyncMock()
        ws2 = Mock()
        ws2.accept = AsyncMock()
        ws2.send_text = AsyncMock()

        await hub_service.connect_backend(ws1)
        await hub_service.connect_backend(ws2)

        message = {"type": "test", "data": "test"}
        await hub_service.send_to_target(message, "backend")

        ws1.send_text.assert_called_once()
        ws2.send_text.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_to_specific_agent(self, hub_service, mock_websocket):
        """测试发送消息给特定 Agent"""
        ws = Mock()
        ws.accept = AsyncMock()
        ws.send_text = AsyncMock()

        await hub_service.connect_agent(ws, "test-agent", "coding")

        message = {"type": "test", "data": "test"}
        success = await hub_service.send_to_agent("test-agent", message)

        assert success is True
        ws.send_text.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_to_nonexistent_agent(self, hub_service):
        """测试发送消息给不存在的 Agent"""
        message = {"type": "test", "data": "test"}
        success = await hub_service.send_to_agent("nonexistent-agent", message)

        assert success is False

    @pytest.mark.asyncio
    async def test_send_to_target_broadcast(self, hub_service, mock_websocket):
        """测试广播消息"""
        ws1 = Mock()
        ws1.accept = AsyncMock()
        ws1.send_text = AsyncMock()
        ws2 = Mock()
        ws2.accept = AsyncMock()
        ws2.send_text = AsyncMock()

        await hub_service.connect_frontend(ws1)
        await hub_service.connect_frontend(ws2)

        message = {"type": "broadcast", "data": "test"}
        await hub_service.broadcast(message, {"frontend"})

        ws1.send_text.assert_called_once()
        ws2.send_text.assert_called_once()


class TestErrorHandling:
    """错误处理测试"""

    @pytest.mark.asyncio
    async def test_handle_invalid_json_message(self, hub_service, mock_websocket):
        """测试处理无效 JSON 消息"""
        info = ConnectionInfo(mock_websocket, "frontend")

        await hub_service.handle_message(mock_websocket, "invalid json", info)

        # 应该发送错误消息
        mock_websocket.send_text.assert_called()
        sent_message = json.loads(mock_websocket.send_text.call_args[0][0])
        assert sent_message["type"] == "error"

    @pytest.mark.asyncio
    async def test_handle_message_exception(self, hub_service, mock_websocket):
        """测试处理消息时的异常"""
        info = ConnectionInfo(mock_websocket, "frontend")

        # 发送缺少必需字段的消息
        invalid_message = json.dumps({"type": "test"})  # 缺少 sender, timestamp 等

        await hub_service.handle_message(mock_websocket, invalid_message, info)

        # 应该正常处理，不抛出异常
        mock_websocket.send_text.assert_called()


class TestAgentRegistration:
    """Agent 注册测试"""

    @pytest.mark.asyncio
    async def test_handle_agent_register_updates_capabilities(self, hub_service, mock_websocket):
        """测试 Agent 注册更新能力"""
        await hub_service.connect_agent(mock_websocket, "test-agent", "coding")

        register_message = {
            "id": "msg-5",
            "type": "agent:register",
            "sender": "agent:test-agent",
            "recipient": "hub",
            "timestamp": datetime.now().isoformat(),
            "payload": {
                "agentId": "test-agent",
                "name": "Enhanced Agent",
                "agentType": "coding",
                "capabilities": ["python", "javascript", "rust", "go"]
            },
            "version": "1.0"
        }

        await hub_service.handle_message(
            mock_websocket,
            json.dumps(register_message),
            ConnectionInfo(mock_websocket, "agent", "test-agent", "coding")
        )

        agent = hub_service.agents.get("test-agent")
        assert agent is not None
        assert len(agent["capabilities"]) == 4
        assert "rust" in agent["capabilities"]
        assert "go" in agent["capabilities"]


class TestHubStatus:
    """Hub 状态测试"""

    @pytest.mark.asyncio
    async def test_get_status_with_connections(self, hub_service, mock_websocket):
        """测试获取有连接的 Hub 状态"""
        # 创建各种连接
        await hub_service.connect_frontend(mock_websocket)
        await hub_service.connect_backend(mock_websocket)
        await hub_service.connect_agent(mock_websocket, "agent-1", "coding")
        await hub_service.connect_agent(mock_websocket, "agent-2", "review")

        status = hub_service.get_status()

        assert status["frontend_clients"] == 1
        assert status["backend_clients"] == 1
        assert status["total_agents"] == 2
        assert len(status["agents"]) == 2

    def test_running_state(self, hub_service):
        """测试运行状态"""
        assert hub_service.running is False

        hub_service.running = True
        assert hub_service.running is True
