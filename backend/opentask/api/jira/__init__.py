"""Jira 线格式兼容层（/rest/api/2，S7）

ADR D13：本机 Orca 无自定义任务源注册面，但其 Jira 集成支持自建实例
（Server/DC，可配 base URL）。本层让 OpenTask 以 Jira REST v2 线格式对
Orca 暴露任务源，与 /tasks 契约层（D12 形状）共用 mapping/auth/schemas
内核，契约端点保持不动。

结构：
- keys.py        OPENTASK-{数字} ↔ issue_code 编解码
- jql.py         Orca 自产 JQL 子集 → 契约过滤条件
- converters.py  Issue → Jira REST v2 投影（status/priority/用户/时间戳）
- auth.py        Basic/Bearer → 契约 access_token 内核（vk_/JWT）
- errors.py      CONTRACT_* 语义 + Jira 形状错误体
- router.py      端点（探测报告 §2/§3 全调用面）

挂载（jira/wiring.py 的 mount_jira_wire）：以独立 FastAPI 子应用承载
路由与异常处理器（错误体恒为 Jira 形状 errorMessages/errors），再经一条
ASGI 转发路由（/rest/api/2/{path}）挂进 tasks 契约路由——FastAPI
include_router 会丢弃路由表里的 Starlette Mount，故不能用路由级 Mount；
转发路由 include_in_schema=False，/tasks 侧 OpenAPI 契约不受污染。
app.py 不属于本 sprint 允许路径，故宿主为 tasks 契约路由（内核共用，
宿主关系一致），见 tasks/__init__.py 与 wiring.py。
"""

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError

from .errors import (
    JiraWireError,
    jira_validation_error_handler,
    jira_wire_error_handler,
)
from .router import router as jira_router

jira_app = FastAPI(
    title="OpenTask Jira Wire Compatibility",
    # 兼容层不需要独立文档端点（OpenAPI 契约在 /tasks 侧维护）
    openapi_url=None,
    docs_url=None,
    redoc_url=None,
)
jira_app.include_router(jira_router)
jira_app.add_exception_handler(JiraWireError, jira_wire_error_handler)
jira_app.add_exception_handler(RequestValidationError, jira_validation_error_handler)

__all__ = ["jira_app"]
