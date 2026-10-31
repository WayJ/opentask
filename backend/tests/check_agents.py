"""
检查 WebSocket Hub 中的 Agent 注册状态
"""

import asyncio

async def check_agents():
    """检查 WebSocket Hub 中的 Agent"""
    try:
        # 获取 Hub 实例
        from opentask.services.websocket.hub_service import get_websocket_hub
        hub = get_websocket_hub()

        print(f"WebSocket Hub 状态:")
        print(f"  前端连接数: {len(hub.frontend_clients)}")
        print(f"  后端连接数: {len(hub.backend_clients)}")
        print(f"  Agent 连接数: {len(hub.agent_clients)}")
        print(f"  注册的 Agent 数: {len(hub.agents)}")

        if hub.agents:
            print(f"\n在线 Agent 列表:")
            for agent_id, info in hub.agents.items():
                print(f"  - {agent_id}")
                print(f"    名称: {info['name']}")
                print(f"    类型: {info['agent_type']}")
                print(f"    状态: {info['status']}")
                print(f"    注册时间: {info['registered_at']}")
                print(f"    能力: {info['capabilities']}")
        else:
            print(f"\n没有 Agent 在线")

    except Exception as e:
        print(f"错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(check_agents())
