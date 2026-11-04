"""
WebSocket Hub 路由 - 集成到 FastAPI
提供前端、后端和 Agent 的 WebSocket 连接端点
"""

import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from opentask.services.websocket.hub_service import get_websocket_hub

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ws", tags=["WebSocket"])


@router.websocket("/hub")
async def websocket_hub_frontend(websocket: WebSocket):
    """前端 WebSocket 连接端点"""
    hub = get_websocket_hub()
    info = await hub.connect_frontend(websocket)

    logger.info(f"Frontend WebSocket connected from {websocket.client}")

    try:
        while True:
            # 接收消息
            raw_message = await websocket.receive_text()
            await hub.handle_message(websocket, raw_message, info)
    except WebSocketDisconnect:
        logger.info(f"Frontend WebSocket disconnected: {websocket.client}")
    except Exception as e:
        logger.error(f"Frontend WebSocket error: {e}", exc_info=True)
    finally:
        await hub.disconnect(websocket, info)


@router.websocket("/hub/backend")
async def websocket_hub_backend(websocket: WebSocket):
    """后端服务 WebSocket 连接端点"""
    hub = get_websocket_hub()
    info = await hub.connect_backend(websocket)

    logger.info(f"Backend WebSocket connected from {websocket.client}")

    try:
        while True:
            # 接收消息
            raw_message = await websocket.receive_text()
            await hub.handle_message(websocket, raw_message, info)
    except WebSocketDisconnect:
        logger.info(f"Backend WebSocket disconnected: {websocket.client}")
    except Exception as e:
        logger.error(f"Backend WebSocket error: {e}", exc_info=True)
    finally:
        await hub.disconnect(websocket, info)


@router.websocket("/hub/agent")
async def websocket_hub_agent(
    websocket: WebSocket,
    agent_id: str = Query(..., description="Agent ID"),
    agent_type: str = Query("coding", description="Agent 类型 (coding, design, review, research 等)")
):
    """Agent WebSocket 连接端点

    Args:
        websocket: WebSocket 连接
        agent_id: Agent 唯一标识
        agent_type: Agent 类型，默认为 coding
    """
    hub = get_websocket_hub()
    info = await hub.connect_agent(websocket, agent_id, agent_type)

    logger.info(f"Agent WebSocket connected: {agent_id} ({agent_type}) from {websocket.client}")

    try:
        while True:
            # 接收消息
            raw_message = await websocket.receive_text()
            await hub.handle_message(websocket, raw_message, info)
    except WebSocketDisconnect:
        logger.info(f"Agent WebSocket disconnected: {agent_id}")
    except Exception as e:
        logger.error(f"Agent WebSocket error for {agent_id}: {e}", exc_info=True)
    finally:
        await hub.disconnect(websocket, info)


@router.websocket("/workspace")
async def websocket_workspace(
    websocket: WebSocket,
    token: str = Query("", description="JWT 或 Access Token"),
    workspace_id: str = Query("", description="目标工作区 ID"),
):
    """Workspace 业务实时通道（E23）。

    鉴权：query token + workspace_id；必须为该工作区成员。
    与 /ws/hub* Agent hub 分离。
    """
    from fastapi import HTTPException
    from opentask.repositories.base import SessionCreator
    from opentask.services.workspace.service import WorkspaceService
    from opentask.services.workspace_realtime.auth import resolve_user_from_token
    from opentask.services.workspace_realtime.hub import get_workspace_realtime_hub

    if not token or not workspace_id:
        # 无参：accept 后立刻关闭，兼容 TestClient
        await websocket.accept()
        await websocket.close(code=4400)
        return

    session = SessionCreator()
    conn = None
    hub = get_workspace_realtime_hub()
    try:
        try:
            user = await resolve_user_from_token(token, session)
            await WorkspaceService(session).require_member(workspace_id, str(user.id))
        except HTTPException as exc:
            await websocket.accept()
            code = 4401 if exc.status_code == 401 else 4403
            await websocket.close(code=code)
            return
        except Exception as exc:  # noqa: BLE001
            logger.error("Workspace WS auth error: %s", exc, exc_info=True)
            await websocket.accept()
            await websocket.close(code=4401)
            return

        await websocket.accept()
        conn = await hub.connect(
            websocket,
            user_id=str(user.id),
            workspace_id=workspace_id,
        )
        await websocket.send_json(
            {
                "type": "connected",
                "workspace_id": workspace_id,
                "connection_id": conn.connection_id,
            }
        )

        while True:
            raw = await websocket.receive_text()
            msg_type = None
            try:
                import json as _json

                parsed = _json.loads(raw)
                msg_type = parsed.get("type") if isinstance(parsed, dict) else None
            except Exception:  # noqa: BLE001
                if raw.strip().lower() == "ping":
                    msg_type = "ping"
            if msg_type == "ping":
                await websocket.send_json({"type": "pong"})
    except WebSocketDisconnect:
        logger.info("Workspace realtime disconnected: %s", workspace_id)
    except Exception as e:
        logger.error("Workspace realtime error: %s", e, exc_info=True)
    finally:
        await hub.disconnect(conn)
        try:
            await session.close()
        except Exception:  # noqa: BLE001
            pass
