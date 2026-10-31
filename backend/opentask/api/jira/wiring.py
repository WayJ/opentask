"""Jira 线格式挂载（ASGI 转发路由，S7）

独立于 jira/__init__ 的最小模块：不在模块顶层导入 jira_app，保证从
tasks/__init__（或任何顺序）导入本模块都不构成环——jira 包的 errors
等子模块反向依赖 tasks 包，挂载点又必须写在 tasks/__init__（app.py 不在
本 sprint 允许路径），import 顺序两个方向都要能走通。

挂载方式（探测报告实现依据见 __init__ 模块 docstring）：FastAPI
include_router 会丢弃路由表里的 Starlette Mount，故注册一条
``/rest/api/2/{path}`` 的 catch-all APIRoute，剥前缀后按 ASGI 协议把请求
转交给子应用 jira_app，再把响应消息重组为 Response 返回；子应用的异常
处理器因此全链路生效（错误体恒为 Jira 形状）。
include_in_schema=False 保证 /tasks 侧 OpenAPI 契约不被污染。
"""

from typing import Dict, List

from fastapi import Request, Response


def mount_jira_wire(tasks_router) -> None:
    """把 /rest/api/2/* 转发路由注册进 tasks 契约路由（幂等：重复调用跳过）"""

    if any(getattr(r, "name", "") == "jira_wire_compat" for r in tasks_router.routes):
        return

    @tasks_router.api_route(
        "/rest/api/2/{jira_path:path}",
        methods=["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"],
        include_in_schema=False,
        name="jira_wire_compat",
        tags=["Jira 线格式 (Jira Wire Compatibility)"],
    )
    async def jira_wire_entrypoint(request: Request, jira_path: str) -> Response:
        # 延迟导入：模块顶层导入会与 jira/__init__ 成环（见模块 docstring）
        from . import jira_app

        scope = dict(request.scope)
        scope["path"] = "/" + (jira_path or "")
        scope["raw_path"] = scope["path"].encode("utf-8")
        # 子应用内部不再感知 /rest/api/2 前缀（Mount 语义）
        scope["root_path"] = (scope.get("root_path") or "") + "/rest/api/2"
        scope.pop("route", None)
        scope.pop("endpoint", None)

        body = await request.body()

        async def receive() -> Dict:
            return {"type": "http.request", "body": body, "more_body": False}

        messages: List[Dict] = []

        async def send(message: Dict) -> None:
            messages.append(message)

        await jira_app(scope, receive, send)

        status = 500
        headers: Dict[str, str] = {}
        content = b""
        for message in messages:
            if message["type"] == "http.response.start":
                status = message["status"]
                headers = {
                    k.decode("latin-1"): v.decode("latin-1")
                    for k, v in message.get("headers", [])
                }
            elif message["type"] == "http.response.body":
                content += message.get("body", b"")
        # content-length 由 Response 按实际 body 重算
        headers.pop("content-length", None)
        media_type = headers.pop("content-type", None)
        return Response(
            content=content, status_code=status, headers=headers, media_type=media_type
        )
