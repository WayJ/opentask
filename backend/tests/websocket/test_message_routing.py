"""
WebSocket 消息路由测试

测试 WebSocket Hub 的消息路由功能：
- 消息类型识别
- 目标客户端路由
- 消息转发
- 错误处理
"""

import pytest
import json
from datetime import datetime
from unittest.mock import Mock, AsyncMock

from opentask.services.websocket.hub_service import (
    WebSocketHubService,
    ConnectionInfo,
)


@pytest.fixture
def hub_service():
    """创建 Hub 服务实例"""
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


class TestTaskSubmitRouting:
    """任务提交消息路由测试"""

    @pytest.mark.asyncio
    async def test_route_task_submit_to_specific_agent(self, hub_service, mock_websocket):
        """测试路由任务提交到特定 Agent"""
        # 创建目标 Agent
        agent_ws = Mock()
        agent_ws.accept = AsyncMock()
        agent_ws.send_text = AsyncMock()
        await hub_service.connect_agent(agent_ws, "coding-agent-1", "coding")

        # 创建任务提交消息
        task_message = {
            "id": "msg-1",
            "type": "task:submit",
            "sender": "frontend",
            "recipient": "agent:coding-agent-1",
            "timestamp": datetime.now().isoformat(),
            "payload": {
                "taskId": "task-123",
                "targetAgentId": "coding-agent-1",
                "title": "实现新功能",
                "description": "需求描述",
                "taskType": "IMPLEMENT",
                "priority": "HIGH"
            },
            "version": "1.0"
        }

        # 路由消息
        await hub_service.route_message(
            task_message,
            ConnectionInfo(mock_websocket, "frontend")
        )

        # 验证 Agent 收到消息
        agent_ws.send_text.assert_called_once()
        sent_message = json.loads(agent_ws.send_text.call_args[0][0])
        assert sent_message["type"] == "task:submit"
        assert sent_message["payload"]["taskId"] == "task-123"

    @pytest.mark.asyncio
    async def test_route_task_submit_to_nonexistent_agent(self, hub_service, mock_websocket):
        """测试路由任务提交到不存在的 Agent"""
        # 不创建任何 Agent

        task_message = {
            "id": "msg-2",
            "type": "task:submit",
            "sender": "frontend",
            "recipient": "agent:nonexistent-agent",
            "timestamp": datetime.now().isoformat(),
            "payload": {
                "targetAgentId": "nonexistent-agent",
                "taskId": "task-456"
            },
            "version": "1.0"
        }

        # 路由消息（不应该抛出异常）
        await hub_service.route_message(
            task_message,
            ConnectionInfo(mock_websocket, "frontend")
        )

        # 应该正常处理，不会崩溃


class TestProgressMessageRouting:
    """进度消息路由测试"""

    @pytest.mark.asyncio
    async def test_route_task_progress_to_frontend(self, hub_service, mock_websocket):
        """测试路由任务进度到前端"""
        # 创建前端连接
        frontend_ws1 = Mock()
        frontend_ws1.accept = AsyncMock()
        frontend_ws1.send_text = AsyncMock()
        frontend_ws2 = Mock()
        frontend_ws2.accept = AsyncMock()
        frontend_ws2.send_text = AsyncMock()

        await hub_service.connect_frontend(frontend_ws1)
        await hub_service.connect_frontend(frontend_ws2)

        # 创建进度消息
        progress_message = {
            "id": "msg-3",
            "type": "task:progress",
            "sender": "agent:coding-agent-1",
            "recipient": "frontend",
            "timestamp": datetime.now().isoformat(),
            "payload": {
                "taskId": "task-123",
                "status": "RUNNING",
                "progress": 50,
                "currentStep": "实现中",
                "message": "正在编写代码"
            },
            "version": "1.0"
        }

        # 路由消息
        await hub_service.route_message(
            progress_message,
            ConnectionInfo(mock_websocket, "agent", "coding-agent-1", "coding")
        )

        # 验证所有前端都收到消息
        frontend_ws1.send_text.assert_called_once()
        frontend_ws2.send_text.assert_called_once()

        sent_message = json.loads(frontend_ws1.send_text.call_args[0][0])
        assert sent_message["type"] == "task:progress"
        assert sent_message["payload"]["progress"] == 50

    @pytest.mark.asyncio
    async def test_route_task_complete_to_frontend(self, hub_service, mock_websocket):
        """测试路由任务完成消息到前端"""
        # 创建前端连接
        frontend_ws = Mock()
        frontend_ws.accept = AsyncMock()
        frontend_ws.send_text = AsyncMock()
        await hub_service.connect_frontend(frontend_ws)

        # 创建完成消息
        complete_message = {
            "id": "msg-4",
            "type": "task:complete",
            "sender": "agent:coding-agent-1",
            "recipient": "frontend",
            "timestamp": datetime.now().isoformat(),
            "payload": {
                "taskId": "task-123",
                "status": "COMPLETED",
                "result": {"output": "任务完成"},
                "executionTimeMs": 5000
            },
            "version": "1.0"
        }

        # 路由消息
        await hub_service.route_message(
            complete_message,
            ConnectionInfo(mock_websocket, "agent", "coding-agent-1", "coding")
        )

        # 验证前端收到消息
        frontend_ws.send_text.assert_called_once()
        sent_message = json.loads(frontend_ws.send_text.call_args[0][0])
        assert sent_message["type"] == "task:complete"
        assert sent_message["payload"]["status"] == "COMPLETED"


class TestAgentMessageRouting:
    """Agent 消息路由测试"""

    @pytest.mark.asyncio
    async def test_route_agent_register_to_all_backends(self, hub_service, mock_websocket):
        """测试路由 Agent 注册消息到所有后端"""
        # 创建后端连接
        backend_ws1 = Mock()
        backend_ws1.accept = AsyncMock()
        backend_ws1.send_text = AsyncMock()
        backend_ws2 = Mock()
        backend_ws2.accept = AsyncMock()
        backend_ws2.send_text = AsyncMock()

        await hub_service.connect_backend(backend_ws1)
        await hub_service.connect_backend(backend_ws2)

        # 创建注册消息
        register_message = {
            "id": "msg-5",
            "type": "agent:register",
            "sender": "agent:coding-agent-1",
            "recipient": "hub",
            "timestamp": datetime.now().isoformat(),
            "payload": {
                "agentId": "coding-agent-1",
                "name": "Coding Agent",
                "agentType": "coding",
                "capabilities": ["python", "javascript"]
            },
            "version": "1.0"
        }

        # 路由消息
        await hub_service.route_message(
            register_message,
            ConnectionInfo(mock_websocket, "agent", "coding-agent-1", "coding")
        )

        # 验证所有后端都收到消息
        backend_ws1.send_text.assert_called_once()
        backend_ws2.send_text.assert_called_once()

    @pytest.mark.asyncio
    async def test_route_agent_heartbeat_to_hub_only(self, hub_service, mock_websocket):
        """测试路由 Agent 心跳消息（仅 Hub 处理）"""
        # 创建前端和后端连接
        frontend_ws = Mock()
        frontend_ws.accept = AsyncMock()
        frontend_ws.send_text = AsyncMock()
        backend_ws = Mock()
        backend_ws.accept = AsyncMock()
        backend_ws.send_text = AsyncMock()

        await hub_service.connect_frontend(frontend_ws)
        await hub_service.connect_backend(backend_ws)
        # 先注册 Agent（心跳更新要求 agents 中已有记录）
        await hub_service.connect_agent(mock_websocket, "coding-agent-1", "coding")

        # 创建心跳消息
        heartbeat_message = {
            "id": "msg-6",
            "type": "agent:heartbeat",
            "sender": "agent:coding-agent-1",
            "recipient": "hub",
            "timestamp": datetime.now().isoformat(),
            "payload": {
                "agentId": "coding-agent-1"
            },
            "version": "1.0"
        }

        # 走真实入口 handle_message：心跳在其中被 Hub 直接处理并提前返回
        await hub_service.handle_message(
            mock_websocket,
            json.dumps(heartbeat_message),
            ConnectionInfo(mock_websocket, "agent", "coding-agent-1", "coding")
        )

        # 心跳消息不转发给前端或后端
        frontend_ws.send_text.assert_not_called()
        backend_ws.send_text.assert_not_called()
        # 心跳时间已在内存中更新（无 DB 回退路径）
        assert "last_heartbeat" in hub_service.agents["coding-agent-1"]


class TestBroadcastRouting:
    """广播路由测试"""

    @pytest.mark.asyncio
    async def test_broadcast_to_all_frontends(self, hub_service, mock_websocket):
        """测试广播消息到所有前端"""
        # 创建多个前端连接
        frontend_ws1 = Mock()
        frontend_ws1.accept = AsyncMock()
        frontend_ws1.send_text = AsyncMock()
        frontend_ws2 = Mock()
        frontend_ws2.accept = AsyncMock()
        frontend_ws2.send_text = AsyncMock()
        frontend_ws3 = Mock()
        frontend_ws3.accept = AsyncMock()
        frontend_ws3.send_text = AsyncMock()

        await hub_service.connect_frontend(frontend_ws1)
        await hub_service.connect_frontend(frontend_ws2)
        await hub_service.connect_frontend(frontend_ws3)

        # 广播消息
        message = {"type": "broadcast", "data": "test"}
        await hub_service.broadcast(message, {"frontend"})

        # 验证所有前端都收到消息
        frontend_ws1.send_text.assert_called_once()
        frontend_ws2.send_text.assert_called_once()
        frontend_ws3.send_text.assert_called_once()

    @pytest.mark.asyncio
    async def test_broadcast_to_multiple_targets(self, hub_service, mock_websocket):
        """测试广播消息到多个目标类型"""
        # 创建前端和后端连接
        frontend_ws = Mock()
        frontend_ws.accept = AsyncMock()
        frontend_ws.send_text = AsyncMock()
        backend_ws = Mock()
        backend_ws.accept = AsyncMock()
        backend_ws.send_text = AsyncMock()

        await hub_service.connect_frontend(frontend_ws)
        await hub_service.connect_backend(backend_ws)

        # 广播消息到前端和后端
        message = {"type": "broadcast", "data": "test"}
        await hub_service.broadcast(message, {"frontend", "backend"})

        # 验证都收到消息
        frontend_ws.send_text.assert_called_once()
        backend_ws.send_text.assert_called_once()


class TestMessageSendingErrors:
    """消息发送错误处理测试"""

    @pytest.mark.asyncio
    async def test_handle_disconnected_frontend_on_send(self, hub_service, mock_websocket):
        """测试处理发送时前端断开连接"""
        # 创建前端连接，但发送时抛出异常
        frontend_ws = Mock()
        frontend_ws.accept = AsyncMock()
        frontend_ws.send_text = AsyncMock(side_effect=Exception("Connection closed"))
        await hub_service.connect_frontend(frontend_ws)

        # 尝试发送消息
        message = {"type": "test", "data": "test"}
        await hub_service.send_to_target(message, "frontend")

        # 验证断开的连接被移除
        assert frontend_ws not in hub_service.frontend_clients

    @pytest.mark.asyncio
    async def test_handle_disconnected_agent_on_send(self, hub_service, mock_websocket):
        """测试处理发送时 Agent 断开连接"""
        # 创建 Agent 连接，但发送时抛出异常
        agent_ws = Mock()
        agent_ws.accept = AsyncMock()
        agent_ws.send_text = AsyncMock(side_effect=Exception("Connection lost"))
        await hub_service.connect_agent(agent_ws, "test-agent", "coding")

        # 尝试发送消息
        message = {"type": "test", "data": "test"}
        success = await hub_service.send_to_agent("test-agent", message)

        # 验证发送失败
        assert success is False
        # 验证 Agent 被清理
        assert "test-agent" not in hub_service.agent_clients
        assert "test-agent" not in hub_service.agents


class TestMessageValidation:
    """消息验证测试"""

    @pytest.mark.asyncio
    async def test_handle_message_with_missing_fields(self, hub_service, mock_websocket):
        """测试处理缺少字段的消息"""
        # 创建缺少必需字段的消息
        invalid_message = json.dumps({
            "type": "test"
            # 缺少 sender, timestamp, payload 等
        })

        # 应该正常处理，不抛出异常
        await hub_service.handle_message(
            mock_websocket,
            invalid_message,
            ConnectionInfo(mock_websocket, "frontend")
        )

        # 应该发送确认（或错误）消息
        mock_websocket.send_text.assert_called()

    @pytest.mark.asyncio
    async def test_handle_malformed_json(self, hub_service, mock_websocket):
        """测试处理格式错误的 JSON"""
        malformed_json = "{invalid json}"

        await hub_service.handle_message(
            mock_websocket,
            malformed_json,
            ConnectionInfo(mock_websocket, "frontend")
        )

        # 应该发送错误消息
        mock_websocket.send_text.assert_called()
        sent_message = json.loads(mock_websocket.send_text.call_args[0][0])
        assert sent_message["type"] == "error"


class TestRoutingEdgeCases:
    """路由边界情况测试"""

    @pytest.mark.asyncio
    async def test_route_message_with_unknown_type(self, hub_service, mock_websocket):
        """测试路由未知类型的消息"""
        unknown_message = {
            "id": "msg-7",
            "type": "unknown:type",
            "sender": "frontend",
            "recipient": "backend",
            "timestamp": datetime.now().isoformat(),
            "payload": {},
            "version": "1.0"
        }

        # 不应该抛出异常
        await hub_service.route_message(
            unknown_message,
            ConnectionInfo(mock_websocket, "frontend")
        )

    @pytest.mark.asyncio
    async def test_route_message_to_all_targets(self, hub_service, mock_websocket):
        """测试路由消息到所有类型的目标"""
        # 创建各种类型的连接
        frontend_ws = Mock()
        frontend_ws.accept = AsyncMock()
        frontend_ws.send_text = AsyncMock()
        backend_ws = Mock()
        backend_ws.accept = AsyncMock()
        backend_ws.send_text = AsyncMock()

        await hub_service.connect_frontend(frontend_ws)
        await hub_service.connect_backend(backend_ws)

        # 使用 "broadcast" 类型路由到所有
        broadcast_message = {
            "id": "msg-8",
            "type": "agent:register",
            "sender": "agent:new-agent",
            "recipient": "hub",
            "timestamp": datetime.now().isoformat(),
            "payload": {
                "agentId": "new-agent",
                "name": "New Agent",
                "agentType": "coding"
            },
            "version": "1.0"
        }

        await hub_service.route_message(
            broadcast_message,
            ConnectionInfo(mock_websocket, "agent", "new-agent", "coding")
        )

        # 应该广播到前端和后端
        frontend_ws.send_text.assert_called()
        backend_ws.send_text.assert_called()

    @pytest.mark.asyncio
    async def test_concurrent_message_routing(self, hub_service, mock_websocket):
        """测试并发消息路由"""
        import asyncio

        # 创建多个连接
        agents = []
        for i in range(5):
            agent_ws = Mock()
            agent_ws.accept = AsyncMock()
            agent_ws.send_text = AsyncMock()
            await hub_service.connect_agent(agent_ws, f"agent-{i}", "coding")
            agents.append(agent_ws)

        # 并发发送多个消息
        tasks = []
        for i in range(10):
            message = {
                "id": f"msg-{i}",
                "type": "task:submit",
                "sender": "frontend",
                "recipient": f"agent:agent-{i % 5}",
                "timestamp": datetime.now().isoformat(),
                "payload": {"taskId": f"task-{i}"},
                "version": "1.0"
            }

            task = hub_service.route_message(
                message,
                ConnectionInfo(mock_websocket, "frontend")
            )
            tasks.append(task)

        # 等待所有任务完成
        await asyncio.gather(*tasks)

        # 验证没有抛出异常
        assert True
