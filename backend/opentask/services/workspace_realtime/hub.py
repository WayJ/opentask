"""WorkspaceRealtimeHub — 进程内按 workspace 广播业务事件。"""

from __future__ import annotations

import asyncio
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

from fastapi import WebSocket

logger = logging.getLogger(__name__)


@dataclass
class WorkspaceConnection:
    websocket: WebSocket
    user_id: str
    workspace_id: str
    connection_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    connected_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class WorkspaceRealtimeHub:
    """按 workspace_id 管理连接并广播事件。"""

    def __init__(self) -> None:
        self._rooms: dict[str, dict[str, WorkspaceConnection]] = {}
        self._lock = asyncio.Lock()

    async def connect(
        self,
        websocket: WebSocket,
        *,
        user_id: str,
        workspace_id: str,
    ) -> WorkspaceConnection:
        conn = WorkspaceConnection(
            websocket=websocket,
            user_id=str(user_id),
            workspace_id=str(workspace_id),
        )
        async with self._lock:
            room = self._rooms.setdefault(conn.workspace_id, {})
            room[conn.connection_id] = conn
        logger.info(
            "workspace realtime connected ws=%s user=%s conn=%s room_size=%s",
            conn.workspace_id,
            conn.user_id,
            conn.connection_id,
            len(self._rooms.get(conn.workspace_id, {})),
        )
        return conn

    async def disconnect(self, conn: WorkspaceConnection | None) -> None:
        if not conn:
            return
        async with self._lock:
            room = self._rooms.get(conn.workspace_id)
            if not room:
                return
            room.pop(conn.connection_id, None)
            if not room:
                self._rooms.pop(conn.workspace_id, None)
        logger.info(
            "workspace realtime disconnected ws=%s user=%s conn=%s",
            conn.workspace_id,
            conn.user_id,
            conn.connection_id,
        )

    def room_size(self, workspace_id: str) -> int:
        return len(self._rooms.get(str(workspace_id), {}))

    async def publish(
        self,
        workspace_id: str,
        event_type: str,
        payload: dict[str, Any],
        *,
        actor_user_id: Optional[str] = None,
        skip_actor: bool = True,
    ) -> int:
        """向 workspace 房间广播；返回成功发送数。"""
        ws_id = str(workspace_id)
        message = {
            "type": event_type,
            "workspace_id": ws_id,
            "ts": datetime.now(timezone.utc).isoformat(),
            "actor_user_id": str(actor_user_id) if actor_user_id else None,
            "payload": payload or {},
        }
        async with self._lock:
            room = list(self._rooms.get(ws_id, {}).values())

        sent = 0
        dead: list[WorkspaceConnection] = []
        for conn in room:
            if (
                skip_actor
                and actor_user_id
                and str(conn.user_id) == str(actor_user_id)
            ):
                continue
            try:
                await conn.websocket.send_json(message)
                sent += 1
            except Exception as exc:  # noqa: BLE001 — best-effort
                logger.warning(
                    "workspace realtime send failed conn=%s: %s",
                    conn.connection_id,
                    exc,
                )
                dead.append(conn)

        for conn in dead:
            await self.disconnect(conn)
        return sent


_hub: Optional[WorkspaceRealtimeHub] = None


def get_workspace_realtime_hub() -> WorkspaceRealtimeHub:
    global _hub
    if _hub is None:
        _hub = WorkspaceRealtimeHub()
    return _hub


def reset_workspace_realtime_hub_for_tests() -> WorkspaceRealtimeHub:
    """测试用：重置单例。"""
    global _hub
    _hub = WorkspaceRealtimeHub()
    return _hub
