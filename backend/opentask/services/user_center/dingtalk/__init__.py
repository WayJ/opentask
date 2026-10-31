"""钉钉集成：开放平台客户端封装 + 通讯录全量同步对账

- client.py：DingTalkClient（接口窄、可 mock，凭据未配置时构造即抛 DingTalkError）
- sync_service.py：DingTalkSyncService（部门/用户全量对账，幂等）
"""
from opentask.services.user_center.dingtalk.client import DingTalkClient, DingTalkError
from opentask.services.user_center.dingtalk.sync_service import DingTalkSyncService

__all__ = ["DingTalkClient", "DingTalkError", "DingTalkSyncService"]
