"""
WebSocket Hub 服务 - 集成到 OpenTask 后端

管理 WebSocket 连接、消息路由和 Agent 注册
使用 FastAPI 的 WebSocket 支持
"""

import asyncio
import json
import logging
from typing import Dict, Set, Optional
from datetime import datetime
from fastapi import WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)


class ConnectionInfo:
    """连接信息"""
    def __init__(
        self,
        websocket: WebSocket,
        client_type: str,  # "frontend", "backend", "agent"
        agent_id: Optional[str] = None,
        agent_type: Optional[str] = None,
        path: str = "/"
    ):
        self.websocket = websocket
        self.client_type = client_type
        self.agent_id = agent_id
        self.agent_type = agent_type
        self.path = path
        self.connected_at = datetime.now()


class WebSocketHubService:
    """WebSocket Hub 服务 - 集成到 FastAPI"""

    def __init__(self, db_session_factory=None):
        # 客户端连接
        self.frontend_clients: Set[WebSocket] = set()
        self.backend_clients: Set[WebSocket] = set()
        self.agent_clients: Dict[str, WebSocket] = {}  # agent_id -> websocket

        # Agent 信息
        self.agents: Dict[str, dict] = {}  # agent_id -> agent info

        # 运行状态
        self.running = False

        # 数据库和生命周期管理
        self.db_session_factory = db_session_factory
        self._heartbeat_task: Optional[asyncio.Task] = None

    async def get_db_session(self):
        """获取数据库 session"""
        if self.db_session_factory:
            return self.db_session_factory()
        return None

    async def start_heartbeat_monitor(self):
        """启动心跳监控任务"""
        if self._heartbeat_task is None or self._heartbeat_task.done():
            self._heartbeat_task = asyncio.create_task(self._heartbeat_monitor_loop())
            logger.info("Heartbeat monitor started")

    async def stop_heartbeat_monitor(self):
        """停止心跳监控任务"""
        if self._heartbeat_task and not self._heartbeat_task.done():
            self._heartbeat_task.cancel()
            try:
                await self._heartbeat_task
            except asyncio.CancelledError:
                pass
            logger.info("Heartbeat monitor stopped")

    async def _heartbeat_monitor_loop(self):
        """心跳监控循环"""
        while self.running:
            try:
                await asyncio.sleep(30)  # 每 30 秒检查一次
                session = await self.get_db_session()
                if session:
                    try:
                        from opentask.services.agent_lifecycle_manager import AgentLifecycleManager

                        lifecycle_manager = AgentLifecycleManager(session)
                        timeout_agents = await lifecycle_manager.check_heartbeat_timeouts()

                        if timeout_agents:
                            logger.warning(f"Found {len(timeout_agents)} agents with heartbeat timeout")
                            for agent in timeout_agents:
                                logger.warning(
                                    f"Agent {agent.agent_id} heartbeat timeout "
                                    f"(misses: {agent.heartbeat_misses})"
                                )

                        await session.commit()
                    finally:
                        await session.close()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in heartbeat monitor: {e}", exc_info=True)

    async def connect_frontend(self, websocket: WebSocket) -> ConnectionInfo:
        """连接前端客户端"""
        await websocket.accept()
        info = ConnectionInfo(websocket, "frontend", path="/")
        self.frontend_clients.add(websocket)
        logger.info(f"Frontend connected: {len(self.frontend_clients)} total")
        return info

    async def connect_backend(self, websocket: WebSocket) -> ConnectionInfo:
        """连接后端客户端"""
        await websocket.accept()
        info = ConnectionInfo(websocket, "backend", path="/backend")
        self.backend_clients.add(websocket)
        logger.info(f"Backend connected: {len(self.backend_clients)} total")
        return info

    async def connect_agent(
        self,
        websocket: WebSocket,
        agent_id: str,
        agent_type: str = "coding"
    ) -> ConnectionInfo:
        """连接 Agent"""
        await websocket.accept()
        info = ConnectionInfo(websocket, "agent", agent_id, agent_type, path="/agent")

        self.agent_clients[agent_id] = websocket

        # 🔥 集成生命周期管理：注册 Agent
        session = await self.get_db_session()
        if session:
            try:
                from opentask.services.agent_lifecycle_manager import AgentLifecycleManager

                lifecycle_manager = AgentLifecycleManager(session)
                agent = await lifecycle_manager.handle_agent_registered(
                    agent_id=agent_id,
                    agent_type=agent_type,
                    agent_name=agent_id,
                )

                # 更新内存中的 Agent 信息
                self.agents[agent_id] = {
                    "agent_id": agent.agent_id,
                    "name": agent.agent_name,
                    "agent_type": agent.agent_type,
                    "capabilities": agent.capabilities or [],
                    "status": agent.status,
                    "connected_at": agent.connected_at.isoformat() if agent.connected_at else None,
                }

                await session.commit()
                logger.info(f"Agent connected and registered: {agent_id} ({agent_type}) - Status: {agent.status}")
            finally:
                await session.close()
        else:
            # 回退到原有行为
            self.agents[agent_id] = {
                "agent_id": agent_id,
                "name": agent_id,
                "agent_type": agent_type,
                "capabilities": [],
                "connected_at": datetime.now().isoformat(),
                "status": "online"
            }
            logger.info(f"Agent connected (no DB): {agent_id} ({agent_type})")

        return info

    async def disconnect(self, websocket: WebSocket, info: ConnectionInfo):
        """断开连接"""
        if info.client_type == "frontend":
            self.frontend_clients.discard(websocket)
        elif info.client_type == "backend":
            self.backend_clients.discard(websocket)
        elif info.client_type == "agent" and info.agent_id:
            # 🔥 集成生命周期管理：记录断开连接
            session = await self.get_db_session()
            if session:
                try:
                    from opentask.services.agent_lifecycle_manager import AgentLifecycleManager

                    lifecycle_manager = AgentLifecycleManager(session)
                    await lifecycle_manager.handle_agent_disconnect(info.agent_id)
                    await session.commit()
                except Exception as e:
                    logger.error(f"Error recording agent disconnect: {e}", exc_info=True)
                finally:
                    await session.close()

            if info.agent_id in self.agent_clients:
                del self.agent_clients[info.agent_id]
            if info.agent_id in self.agents:
                del self.agents[info.agent_id]
            logger.info(f"Agent disconnected: {info.agent_id}")

    async def handle_message(self, websocket: WebSocket, raw_message: str, info: ConnectionInfo):
        """处理接收到的消息"""
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
                agent_id = payload.get("agentId", "")
                if agent_id and agent_id in self.agents:
                    # 🔥 集成生命周期管理：处理心跳
                    session = await self.get_db_session()
                    if session:
                        try:
                            from opentask.services.agent_lifecycle_manager import AgentLifecycleManager

                            lifecycle_manager = AgentLifecycleManager(session)
                            agent = await lifecycle_manager.handle_heartbeat(agent_id)

                            # 更新内存中的状态
                            self.agents[agent_id]["status"] = agent.status
                            self.agents[agent_id]["last_heartbeat"] = datetime.now().isoformat()

                            await session.commit()
                        finally:
                            await session.close()
                    else:
                        # 回退到原有行为
                        self.agents[agent_id]["last_heartbeat"] = datetime.now().isoformat()

                    logger.debug(f"Heartbeat from {agent_id}")
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
            await websocket.send_text(json.dumps(ack))

        except json.JSONDecodeError:
            logger.error("Invalid JSON message")
            await websocket.send_text(json.dumps({"type": "error", "message": "Invalid JSON"}))
        except Exception as e:
            logger.error(f"Error handling message: {e}", exc_info=True)

    async def handle_agent_register(self, websocket: WebSocket, message: dict, info: ConnectionInfo):
        """处理 Agent 注册"""
        payload = message.get("payload", {})

        agent_id = payload.get("agentId", info.agent_id)
        # 支持 name 和 agentName 两种字段
        name = payload.get("name") or payload.get("agentName", agent_id)
        agent_type = payload.get("agentType") or payload.get("agent_type", info.agent_type)
        capabilities = payload.get("capabilities", [])

        # 🔥 集成生命周期管理：更新注册信息
        session = await self.get_db_session()
        if session:
            try:
                from opentask.services.agent_lifecycle_manager import AgentLifecycleManager

                lifecycle_manager = AgentLifecycleManager(session)
                agent = await lifecycle_manager.handle_agent_registered(
                    agent_id=agent_id,
                    agent_type=agent_type,
                    agent_name=name,
                    capabilities=capabilities,
                )

                # 更新内存中的 Agent 信息
                self.agents[agent_id] = {
                    "agent_id": agent.agent_id,
                    "name": agent.agent_name,
                    "agent_type": agent.agent_type,
                    "capabilities": agent.capabilities or [],
                    "status": agent.status,
                    "connected_at": agent.connected_at.isoformat() if agent.connected_at else None,
                }

                await session.commit()
                logger.info(f"Agent registered in DB: {name} ({agent_id} - {agent_type}) - Status: {agent.status}")
            finally:
                await session.close()

        # 回退：更新内存中的 Agent 信息（与 DB 路径一致，注册消息应无条件 upsert，
        # 否则 Agent 后续携带 capabilities 的注册信息会被忽略）
        if agent_id:
            self.agents[agent_id] = {
                "agent_id": agent_id,
                "name": name,
                "agent_type": agent_type,
                "capabilities": capabilities,
                "registered_at": datetime.now().isoformat(),
                "last_heartbeat": datetime.now().isoformat(),
                "status": "online"
            }

            logger.info(f"Agent registered (memory only): {name} ({agent_id} - {agent_type})")

        # 广播给 frontend/backend
        await self.broadcast(message, {"frontend", "backend"})

    async def route_message(self, message: dict, sender_info: ConnectionInfo):
        """路由消息到目标客户端"""
        msg_type = message.get("type", "")
        recipient = message.get("recipient", "")
        payload = message.get("payload", {})

        targets = set()

        # task:submit -> 发送给 Agent
        if msg_type == "task:submit":
            target_agent_id = payload.get("targetAgentId", "")
            if target_agent_id and target_agent_id in self.agent_clients:
                targets.add(target_agent_id)

        # task:progress, task:complete -> 发送给 frontend 并更新数据库
        elif msg_type in ["task:progress", "task:complete"]:
            targets.add("frontend")

            # 🔥 新增：更新数据库中的任务状态
            await self._update_task_in_database(msg_type, payload)

        # agent:register, agent:heartbeat -> 广播
        elif msg_type.startswith("agent:"):
            targets.add("frontend")
            targets.add("backend")

        # 发送消息
        for target in targets:
            await self.send_to_target(message, target)

    async def _update_task_in_database(self, msg_type: str, payload: dict):
        """更新数据库中的任务状态"""
        try:
            from opentask.services.mission_center.service import get_task_service, TaskStatus

            task_id = payload.get("taskId") or payload.get("task_id")
            if not task_id:
                return

            service = get_task_service()
            task = service.get_task(task_id)

            if not task:
                logger.warning(f"Task not found: {task_id}")
                return

            # 更新任务状态
            if msg_type == "task:progress":
                # 🔥 构造进度历史条目
                progress_entry = {
                    "percentage": payload.get("progress", 0),
                    "step": payload.get("currentStep") or payload.get("current_step") or "",
                    "message": payload.get("message", ""),  # AI 的思考文本
                    "timestamp": datetime.now().isoformat()
                }

                service.update_task_status(
                    task_id=task_id,
                    status=TaskStatus.IN_PROGRESS,
                    progress_percentage=payload.get("progress", 0),
                    current_step=payload.get("currentStep") or payload.get("current_step") or "",
                    progress_history_entry=progress_entry  # 🔥 保存进度历史
                )
                logger.info(f"Updated task {task_id} progress to {payload.get('progress', 0)}% with history")

            elif msg_type == "task:complete":
                status = TaskStatus.COMPLETED if payload.get("status") == "COMPLETED" else TaskStatus.FAILED

                # 🔥 最后一次进度更新（完成）
                progress_entry = {
                    "percentage": 100,
                    "step": "完成",
                    "message": payload.get("summary", "任务已完成"),
                    "timestamp": datetime.now().isoformat()
                }

                service.update_task_status(
                    task_id=task_id,
                    status=status,
                    progress_percentage=100,
                    current_step="完成",
                    progress_history_entry=progress_entry
                )
                logger.info(f"Task {task_id} marked as {status} with final history")

        except Exception as e:
            logger.error(f"Error updating task in database: {e}", exc_info=True)

    async def send_to_target(self, message: dict, target: str):
        """发送消息给指定目标"""
        message_json = json.dumps(message)

        if target == "frontend":
            # 广播给所有前端（迭代副本：循环体内会移除失效连接，直接迭代集合会 RuntimeError）
            for ws in list(self.frontend_clients):
                try:
                    await ws.send_text(message_json)
                except Exception as e:
                    logger.error(f"Error sending to frontend: {e}")
                    # 移除断开的连接
                    self.frontend_clients.discard(ws)

        elif target == "backend":
            # 广播给所有后端（同样迭代副本）
            for ws in list(self.backend_clients):
                try:
                    await ws.send_text(message_json)
                except Exception as e:
                    logger.error(f"Error sending to backend: {e}")
                    self.backend_clients.discard(ws)

        elif target in self.agent_clients:
            # 发送给特定 Agent
            try:
                await self.agent_clients[target].send_text(message_json)
            except Exception as e:
                logger.error(f"Error sending to agent {target}: {e}")
                # 移除断开的 Agent
                del self.agent_clients[target]
                if target in self.agents:
                    del self.agents[target]

    async def broadcast(self, message: dict, targets: Optional[set] = None):
        """广播消息"""
        if targets is None:
            targets = {"frontend", "backend"}

        for target in targets:
            await self.send_to_target(message, target)

    async def broadcast_to_all(self, message: dict):
        """广播消息给所有连接（包括所有 Agents）"""
        # 广播给所有前端
        for ws in self.frontend_clients:
            try:
                await ws.send_text(json.dumps(message))
            except Exception as e:
                logger.error(f"Error sending to frontend: {e}")
                self.frontend_clients.discard(ws)

        # 广播给所有后端
        for ws in self.backend_clients:
            try:
                await ws.send_text(json.dumps(message))
            except Exception as e:
                logger.error(f"Error sending to backend: {e}")
                self.backend_clients.discard(ws)

        # 广播给所有 Agents
        for agent_id, ws in self.agent_clients.items():
            try:
                await ws.send_text(json.dumps(message))
            except Exception as e:
                logger.error(f"Error sending to agent {agent_id}: {e}")
                del self.agent_clients[agent_id]
                if agent_id in self.agents:
                    del self.agents[agent_id]

    async def send_to_agent(self, agent_id: str, message: dict) -> bool:
        """发送消息给特定 Agent"""
        if agent_id not in self.agent_clients:
            return False

        try:
            await self.agent_clients[agent_id].send_text(json.dumps(message))
            return True
        except Exception as e:
            logger.error(f"Error sending to agent {agent_id}: {e}")
            # 清理断开的 Agent
            del self.agent_clients[agent_id]
            if agent_id in self.agents:
                del self.agents[agent_id]
            return False

    def get_online_agents(self) -> list:
        """获取在线 Agent 列表"""
        return [
            {
                "agent_id": agent_id,
                **agent_info
            }
            for agent_id, agent_info in self.agents.items()
        ]

    def get_status(self) -> dict:
        """获取 Hub 状态"""
        return {
            "running": self.running,
            "frontend_clients": len(self.frontend_clients),
            "backend_clients": len(self.backend_clients),
            "agents": self.get_online_agents(),
            "total_agents": len(self.agents)
        }


# 全局单例
_websocket_hub: Optional[WebSocketHubService] = None


def get_websocket_hub(db_session_factory=None) -> WebSocketHubService:
    """获取 WebSocket Hub 服务单例"""
    global _websocket_hub
    if _websocket_hub is None:
        _websocket_hub = WebSocketHubService(db_session_factory)
        _websocket_hub.running = True

        # 启动心跳监控
        asyncio.create_task(_websocket_hub.start_heartbeat_monitor())

    return _websocket_hub
