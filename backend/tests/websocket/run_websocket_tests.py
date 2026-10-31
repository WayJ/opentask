"""
WebSocket Hub 单元测试脚本

不使用 pytest，避免数据库迁移问题
"""

import sys
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from unittest.mock import Mock, AsyncMock
from datetime import datetime

from opentask.services.websocket.hub_service import (
    WebSocketHubService,
    ConnectionInfo,
    get_websocket_hub,
)


def create_mock_websocket():
    """创建模拟 WebSocket"""
    ws = Mock()
    ws.accept = AsyncMock()
    ws.send_text = AsyncMock()
    ws.receive_text = AsyncMock()
    ws.close = AsyncMock()
    return ws


class TestResults:
    """测试结果统计"""
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.errors = []

    def add_pass(self, test_name):
        self.passed += 1
        print(f"[PASS] {test_name}")

    def add_fail(self, test_name, error):
        self.failed += 1
        self.errors.append((test_name, error))
        print(f"[FAIL] {test_name}: {error}")

    def summary(self):
        total = self.passed + self.failed
        print("\n" + "=" * 70)
        print(f"测试总结: {self.passed}/{total} 通过")
        if self.failed > 0:
            print(f"\n失败的测试:")
            for test_name, error in self.errors:
                print(f"  - {test_name}: {error}")
        print("=" * 70)
        return self.failed == 0


def test_connection_info(results):
    """测试 ConnectionInfo 类"""
    print("\n=== ConnectionInfo 测试 ===")

    # 测试前端连接信息
    try:
        info = ConnectionInfo(None, "frontend", path="/")
        assert info.client_type == "frontend"
        assert info.path == "/"
        results.add_pass("create_frontend_connection_info")
    except Exception as e:
        results.add_fail("create_frontend_connection_info", str(e))

    # 测试后端连接信息
    try:
        info = ConnectionInfo(None, "backend", path="/backend")
        assert info.client_type == "backend"
        assert info.path == "/backend"
        results.add_pass("create_backend_connection_info")
    except Exception as e:
        results.add_fail("create_backend_connection_info", str(e))

    # 测试 Agent 连接信息
    try:
        info = ConnectionInfo(None, "agent", "test-agent", "coding", path="/agent")
        assert info.client_type == "agent"
        assert info.agent_id == "test-agent"
        assert info.agent_type == "coding"
        results.add_pass("create_agent_connection_info")
    except Exception as e:
        results.add_fail("create_agent_connection_info", str(e))


def test_hub_initialization(results):
    """测试 Hub 服务初始化"""
    print("\n=== Hub 初始化测试 ===")

    try:
        hub = WebSocketHubService()
        assert hub.frontend_clients == set()
        assert hub.backend_clients == set()
        assert hub.agent_clients == {}
        assert hub.agents == {}
        assert hub.running is False
        results.add_pass("hub_service_initialization")
    except Exception as e:
        results.add_fail("hub_service_initialization", str(e))

    try:
        hub1 = get_websocket_hub()
        hub2 = get_websocket_hub()
        assert hub1 is hub2
        assert hub1.running is True
        results.add_pass("singleton_pattern")
    except Exception as e:
        results.add_fail("singleton_pattern", str(e))


def test_hub_status(results):
    """测试 Hub 状态"""
    print("\n=== Hub 状态测试 ===")

    try:
        hub = get_websocket_hub()
        status = hub.get_status()
        assert "running" in status
        assert "frontend_clients" in status
        assert "backend_clients" in status
        assert "agents" in status
        assert "total_agents" in status
        results.add_pass("get_hub_status")
    except Exception as e:
        results.add_fail("get_hub_status", str(e))


def test_agent_management(results):
    """测试 Agent 管理"""
    print("\n=== Agent 管理测试 ===")

    try:
        hub = get_websocket_hub()
        # 模拟添加 Agent
        hub.agents["test-agent-1"] = {
            "agent_id": "test-agent-1",
            "name": "Test Agent 1",
            "agent_type": "coding",
            "capabilities": ["python", "javascript"],
            "connected_at": "2024-01-01T00:00:00",
            "status": "online"
        }

        agents = hub.get_online_agents()
        assert len(agents) == 1
        assert agents[0]["agent_id"] == "test-agent-1"

        # 清理
        del hub.agents["test-agent-1"]
        results.add_pass("agent_management")
    except Exception as e:
        results.add_fail("agent_management", str(e))


def test_message_validation(results):
    """测试消息验证"""
    print("\n=== 消息验证测试 ===")

    import json

    try:
        hub = get_websocket_hub()
        ws = create_mock_websocket()
        info = ConnectionInfo(ws, "frontend")

        # 测试无效 JSON
        import asyncio
        asyncio.run(hub.handle_message(ws, "invalid json", info))

        # 验证发送了错误消息
        ws.send_text.assert_called()
        sent_message = json.loads(ws.send_text.call_args[0][0])
        assert sent_message["type"] == "error"
        results.add_pass("handle_invalid_json")
    except Exception as e:
        results.add_fail("handle_invalid_json", str(e))


def main():
    """运行所有测试"""
    print("\n" + "=" * 70)
    print("WebSocket Hub 单元测试")
    print("=" * 70)

    results = TestResults()

    # 运行测试
    test_connection_info(results)
    test_hub_initialization(results)
    test_hub_status(results)
    test_agent_management(results)
    test_message_validation(results)

    # 打印总结
    success = results.summary()

    if success:
        print("\n[SUCCESS] 所有测试通过！")
        return 0
    else:
        print(f"\n[FAIL] {results.failed} 个测试失败")
        return 1


if __name__ == "__main__":
    exit(main())
