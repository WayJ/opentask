"""钉钉同步 API：通讯录全量同步对账

POST /api/dingtalk/sync：require_permission("manage:dingtalk:sync") →
DingTalkSyncService.sync_all → 返回 diff 报告
（{depts: {created, updated, disabled}, users: {created, updated, disabled}}）。

凭据未配置（DINGTALK_APP_KEY / DINGTALK_APP_SECRET 为空）→ 400
"未配置钉钉应用凭据"；钉钉 API 调用失败（DingTalkError）→ 502。
"""
import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException

from opentask.api.user_center.deps import require_permission
from opentask.config import config
from opentask.models.user.model import UserModel
from opentask.repositories.base import get_session
from opentask.services.user_center.dingtalk.client import DingTalkClient, DingTalkError
from opentask.services.user_center.dingtalk.sync_service import DingTalkSyncService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/dingtalk", tags=["钉钉同步"])


def _build_client() -> DingTalkClient:
    """按配置构造钉钉客户端；未配置凭据 → 400（同步接口禁止空凭据调用）"""
    if not (config.dingtalk_app_key and config.dingtalk_app_secret):
        raise HTTPException(status_code=400, detail="未配置钉钉应用凭据")
    try:
        return DingTalkClient(config.dingtalk_app_key, config.dingtalk_app_secret)
    except DingTalkError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.post("/sync")
async def sync_dingtalk(
    current_user: UserModel = require_permission("manage:dingtalk:sync"),
    session=Depends(get_session),
) -> dict:
    """触发钉钉通讯录全量同步对账（幂等，钉钉为准）"""
    client = _build_client()
    try:
        result = await DingTalkSyncService(session, client).sync_all()
    except DingTalkError as e:
        logger.error(f"钉钉同步失败: {e}")
        raise HTTPException(status_code=502, detail=f"钉钉同步失败: {e}") from e
    return {
        "code": 200,
        "message": "success",
        "data": result,
        "timestamp": int(datetime.now().timestamp() * 1000),
    }
