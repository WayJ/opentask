"""OAuth2 Provider API 模块

端点分两类：

- **标准协议端点**：``/oauth2/token``、``/oauth2/userinfo``、``/oauth2/revoke``
  （消费者服务端直连）；
- **只读数据面**：``/oauth2/api/*``（薄封装既有 service 层）。

浏览器授权入口是**前端 SPA 路由** ``/oauth2/authorize``（前后端分离部署，
浏览器导航不带 Authorization 头），其配套的校验/决策端点在
``/api/oauth2/authorize/*``（需 OpenTask 会话）。
"""

from .read_api import router as read_router
from .router import router

__all__ = ["router", "read_router"]
