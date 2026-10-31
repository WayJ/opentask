"""
WebSocket Hub 集成测试

验证 WebSocket Hub 服务和路由是否正确集成到 FastAPI 应用中
"""

import sys
import asyncio
from pathlib import Path

import pytest

# 添加项目路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from opentask.services.websocket.hub_service import get_websocket_hub, WebSocketHubService
from opentask.api.websocket import router as websocket_router


@pytest.mark.asyncio
async def test_websocket_hub_service():
    """测试 WebSocket Hub 服务初始化

    get_websocket_hub 内部用 asyncio.create_task 启动心跳监控，
    必须在事件循环内调用，故本测试为 async。
    """
    print("[TEST 1] WebSocket Hub Service 初始化")

    hub = get_websocket_hub()
    assert hub is not None, "Hub service should not be None"
    assert isinstance(hub, WebSocketHubService), f"Hub should be WebSocketHubService, got {type(hub)}"

    status = hub.get_status()
    assert "running" in status, "Status should contain 'running'"
    assert "frontend_clients" in status, "Status should contain 'frontend_clients'"
    assert "backend_clients" in status, "Status should contain 'backend_clients'"
    assert "agents" in status, "Status should contain 'agents'"

    # 清理：停止心跳监控（保留全局单例本身，与其它用例共享）
    hub.running = False
    await hub.stop_heartbeat_monitor()

    print(f"[PASS] Hub service initialized successfully")
    print(f"[INFO] Hub status: {status}")
    print()


def test_websocket_router():
    """测试 WebSocket 路由注册"""
    print("[TEST 2] WebSocket Router 注册")

    assert websocket_router is not None, "WebSocket router should not be None"
    assert websocket_router.prefix == "/ws", f"Router prefix should be '/ws', got '{websocket_router.prefix}'"

    routes = websocket_router.routes
    print(f"[INFO] Found {len(routes)} WebSocket routes:")

    route_paths = []
    for route in routes:
        if hasattr(route, 'path'):
            route_paths.append(route.path)
            print(f"  - {route.path}")

    expected_routes = ["/ws/hub", "/ws/hub/backend", "/ws/hub/agent"]
    for expected in expected_routes:
        assert expected in route_paths, f"Expected route '{expected}' not found"

    print(f"[PASS] All expected WebSocket routes are registered")
    print()


def test_connection_info():
    """测试 ConnectionInfo 类"""
    print("[TEST 3] ConnectionInfo 类")

    from opentask.services.websocket.hub_service import ConnectionInfo

    # 测试前端连接信息
    info = ConnectionInfo(None, "frontend", path="/")
    assert info.client_type == "frontend"
    assert info.path == "/"

    # 测试 Agent 连接信息
    info = ConnectionInfo(None, "agent", "test-agent", "coding", path="/agent")
    assert info.client_type == "agent"
    assert info.agent_id == "test-agent"
    assert info.agent_type == "coding"

    print(f"[PASS] ConnectionInfo class works correctly")
    print()


@pytest.mark.asyncio
async def test_singleton_pattern():
    """测试单例模式（get_websocket_hub 首次调用需要事件循环来启动心跳监控）"""
    print("[TEST 4] 单例模式")

    hub1 = get_websocket_hub()
    hub2 = get_websocket_hub()

    assert hub1 is hub2, "get_websocket_hub() should return the same instance"

    # 清理心跳监控任务，避免遗留 pending task
    hub1.running = False
    await hub1.stop_heartbeat_monitor()

    print(f"[PASS] Singleton pattern works correctly")
    print()


def test_agent_management():
    """测试 Agent 管理"""
    print("[TEST 5] Agent 管理")

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
    assert len(agents) == 1, f"Should have 1 agent, got {len(agents)}"
    assert agents[0]["agent_id"] == "test-agent-1"

    # 清理
    del hub.agents["test-agent-1"]

    print(f"[PASS] Agent management works correctly")
    print()


def main():
    """运行所有测试"""
    print("=" * 60)
    print("WebSocket Hub 集成测试")
    print("=" * 60)
    print()

    try:
        test_websocket_hub_service()
        test_websocket_router()
        test_connection_info()
        test_singleton_pattern()
        test_agent_management()

        print("=" * 60)
        print("[SUCCESS] 所有测试通过!")
        print("=" * 60)
        print()
        print("接下来的步骤:")
        print("1. 启动后端服务: uv run uvicorn opentask.main:app --port 7377 --host 0.0.0.0")
        print("2. 启动前端服务: cd frontend && npm run dev")
        print("3. 在浏览器访问: http://localhost:9527/agent-task")
        print("4. 检查浏览器控制台的 WebSocket 连接状态")
        print()

        return 0

    except AssertionError as e:
        print(f"[FAIL] 测试失败: {e}")
        return 1
    except Exception as e:
        print(f"[ERROR] 测试出错: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit(main())
