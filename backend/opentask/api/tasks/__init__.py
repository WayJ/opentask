"""任务源契约 API 模块（OpenTask 对接 Orca 通用任务模型）

S7 起同时承载 Jira 线格式兼容层：/rest/api/2/* 经 ASGI 转发路由挂在本
契约路由下（app.py 不属于本 sprint 允许路径；Jira 层与本层共用
mapping/auth/schemas 内核，宿主关系一致，见 opentask/api/jira/）。
"""
from .router import router

from opentask.api.jira.wiring import mount_jira_wire

mount_jira_wire(router)

__all__ = ["router"]
