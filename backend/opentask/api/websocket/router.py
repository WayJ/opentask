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
