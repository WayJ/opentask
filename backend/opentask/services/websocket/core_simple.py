"""
WebSocket Hub - 核心类 (简化版)

管理 WebSocket 连接、消息路由和 Agent 注册
"""

import asyncio
import json
import logging
from typing import Optional, Dict
from dataclasses import dataclass, field
from datetime import datetime

import websockets
from websockets.server import WebSocketServerProtocol

logger = logging.getLogger(__name__)


@dataclass
class ConnectionInfo:
    """连接信息"""
    websocket: WebSocketServerProtocol
    path: str
    client_type: str  # "frontend", "backend", "agent"
    agent_id: Optional[str] = None
    agent_type: Optional[str] = None


class WebSocketHub:
    """WebSocket Hub 主类 - 简化版"""

    def __init__(self, host: str = "localhost", port: int = 8765, auth_enabled: bool = False):
        self.host = host
        self.port = port
        self.auth_enabled = auth_enabled

        # 客户端连接
        self.frontend_clients = set()
        self.backend_clients = set()
        self.agent_clients = {}  # agent_id -> websocket

        # Agent 信息
        self.agents = {}  # agent_id -> info

        self.running = False

    async def start(self):
        """启动 WebSocket Hub"""
        logger.info(f"Starting WebSocket Hub on ws://{self.host}:{self.port}")
        logger.info(f"  - Frontend: ws://{self.host}:{self.port}/")
        logger.info(f"  - Backend:  ws://{self.host}:{self.port}/backend")
        logger.info(f"  - Agent:    ws://{self.host}:{self.port}/agent")
        logger.info(f"  - Auth:    {'enabled' if self.auth_enabled else 'disabled'}")

        self.running = True

        async with websockets.serve(self.handler, self.host, self.port):
            await asyncio.Future()

    async def handler(self, websocket: WebSocketServerProtocol):
        """WebSocket 连接处理"""
        # 获取路径
        path = websocket.request.path if hasattr(websocket, 'request') else '/'

        # 解析连接类型
        conn_info = self.parse_path(path, websocket)

        # 注册连接
        await self.register_client(websocket, conn_info)

        logger.info(f"Client connected: {conn_info.client_type} ({path})")

        try:
            async for message in websocket:
                await self.handle_message(websocket, message, conn_info)
        except websockets.exceptions.ConnectionClosed as e:
            logger.info(f"Connection closed: {e.code} {e.reason}")
        except Exception as e:
            logger.error(f"Error: {e}", exc_info=True)
        finally:
            await self.unregister_client(websocket, conn_info)

    def parse_path(self, path: str, websocket: WebSocketServerProtocol) -> ConnectionInfo:
        """解析连接路径"""
        # 解析 query 参数
        query = {}
        if '?' in path:
            base, qs = path.split('?', 1)
            for param in qs.split('&'):
                if '=' in param:
                    k, v = param.split('=', 1)
                    query[k] = v
            path = base

        # Agent: /agent
        if path == "/agent":
            return ConnectionInfo(
                websocket=websocket,
                path=path,
                client_type="agent",
                agent_id=query.get("agentId", ""),
                agent_type=query.get("agentType", "coding"),
            )

        # Backend: /backend
        if path == "/backend":
            return ConnectionInfo(
                websocket=websocket,
                path=path,
                client_type="backend",
            )

        # Frontend: 其他
        return ConnectionInfo(
            websocket=websocket,
            path=path,
            client_type="frontend",
        )

    async def register_client(self, websocket: WebSocketServerProtocol, info: ConnectionInfo):
        """注册客户端"""
        if info.client_type == "frontend":
            self.frontend_clients.add(websocket)
        elif info.client_type == "backend":
            self.backend_clients.add(websocket)
        elif info.client_type == "agent":
            if info.agent_id:
                self.agent_clients[info.agent_id] = websocket
                self.agents[info.agent_id] = {
                    "agent_id": info.agent_id,
                    "agent_type": info.agent_type,
                    "connected_at": datetime.now().isoformat(),
                }
                logger.info(f"Agent registered: {info.agent_id} ({info.agent_type})")

    async def unregister_client(self, websocket: WebSocketServerProtocol, info: ConnectionInfo):
        """注销客户端"""
        if info.client_type == "frontend":
            self.frontend_clients.discard(websocket)
        elif info.client_type == "backend":
            self.backend_clients.discard(websocket)
        elif info.client_type == "agent":
            if info.agent_id and info.agent_id in self.agent_clients:
                del self.agent_clients[info.agent_id]
                del self.agents[info.agent_id]
                logger.info(f"Agent unregistered: {info.agent_id}")

    async def handle_message(self, websocket: WebSocketServerProtocol, raw_message: str, info: ConnectionInfo):
        """处理消息"""
        try:
            message = json.loads(raw_message)
            msg_type = message.get("type", "")
            sender = message.get("sender", "")
            payload = message.get("payload", {})

            logger.info(f"Received: {msg_type} from {sender}")

            # 处理 Agent 注册
            if msg_type == "agent:register":
                await self.handle_agent_register(websocket, message, info)
                return

            # 处理心跳
            if msg_type == "agent:heartbeat":
                logger.debug(f"Heartbeat from {payload.get('agentId')}")
                # 可以更新 Agent 状态
                return

            # 路由消息
            await self.route_message(message, info)

            # 发送确认
            ack = {
                "id": message.get("id", ""),
                "type": "system:ack",
                "sender": "hub",
                "recipient": sender,
                "timestamp": datetime.now().isoformat(),
                "payload": {"originalId": message.get("id"), "status": "processed"},
                "version": "1.0"
            }
            await websocket.send(json.dumps(ack))

        except json.JSONDecodeError:
            logger.error("Invalid JSON")
            await websocket.send(json.dumps({"type": "error", "message": "Invalid JSON"}))
        except Exception as e:
            logger.error(f"Error handling message: {e}", exc_info=True)

    async def handle_agent_register(self, websocket: WebSocketServerProtocol, message: dict, info: ConnectionInfo):
        """处理 Agent 注册"""
        payload = message.get("payload", {})

        agent_id = payload.get("agentId", info.agent_id)
        name = payload.get("name", agent_id)
        agent_type = payload.get("agentType", info.agent_type)

        # 更新 Agent 信息
        if agent_id:
            self.agents[agent_id] = {
                "agent_id": agent_id,
                "name": name,
                "agent_type": agent_type,
                "capabilities": payload.get("capabilities", []),
                "registered_at": datetime.now().isoformat(),
            }

            logger.info(f"Agent registered: {agent_id} ({agent_type})")

            # 广播给 frontend/backend
            await self.broadcast(message, {"frontend", "backend"})

        # 发送确认
        ack = {
            "id": message.get("id", ""),
            "type": "system:ack",
            "sender": "hub",
            "recipient": f"agent:{agent_id}",
            "timestamp": datetime.now().isoformat(),
            "payload": {"originalId": message.get("id"), "status": "processed", "message": f"Registered as {name}"},
            "version": "1.0"
        }
        await websocket.send(json.dumps(ack))

    async def route_message(self, message: dict, sender_info: ConnectionInfo):
        """路由消息"""
        msg_type = message.get("type", "")
        recipient = message.get("recipient", "")
        payload = message.get("payload", {})

        targets = set()

        # task:submit -> 发送给 Agent
        if msg_type == "task:submit":
            target_agent = payload.get("targetAgent", "")
            target_agent_id = payload.get("targetAgentId", "")

            # 精确匹配
            if target_agent_id and target_agent_id in self.agent_clients:
                targets.add(target_agent_id)
            # 类型匹配
            elif target_agent:
                for aid, atype in [(a, self.agents[a].get("agent_type")) for a in self.agents]:
                    if atype == target_agent:
                        targets.add(aid)

        # task:progress, task:complete -> 发送给 frontend/backend
        elif msg_type.startswith("task:progress") or msg_type.startswith("task:complete"):
            targets.add("frontend")
            targets.add("backend")

        # agent:register, agent:heartbeat -> 广播
        elif msg_type.startswith("agent:"):
            targets.add("frontend")
            targets.add("backend")

        # 发送消息
        for target in targets:
            await self.send_to_target(message, target, sender_info)

    async def send_to_target(self, message: dict, target: str, exclude: ConnectionInfo):
        """发送给指定目标"""
        if target == "frontend":
            for ws in self.frontend_clients:
                try:
                    await ws.send(json.dumps(message))
                except Exception as e:
                    logger.error(f"Error sending to frontend: {e}")
        elif target == "backend":
            for ws in self.backend_clients:
                try:
                    await ws.send(json.dumps(message))
                except Exception as e:
                    logger.error(f"Error sending to backend: {e}")
        elif target in self.agent_clients:
            try:
                await self.agent_clients[target].send(json.dumps(message))
            except Exception as e:
                logger.error(f"Error sending to agent {target}: {e}")

    async def broadcast(self, message: dict, targets: set):
        """广播消息"""
        for target in targets:
            await self.send_to_target(message, target, None)

    def get_status(self) -> dict:
        """获取状态"""
        return {
            "running": self.running,
            "frontend_clients": len(self.frontend_clients),
            "backend_clients": len(self.backend_clients),
            "agents": list(self.agents.keys()),
        }


async def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="OpenTask WebSocket Hub")
    parser.add_argument("--host", default="localhost")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--no-auth", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    hub = WebSocketHub(args.host, args.port, auth_enabled=not args.no_auth)
    await hub.start()


if __name__ == "__main__":
    asyncio.run(main())
