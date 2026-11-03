"""
SSO Token 认证中间件

验证 SSO token 并同步用户信息到本地数据库
"""
import logging
from typing import Callable

from fastapi import HTTPException, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from opentask.config import config
from opentask.repositories.base import AsyncSession
from opentask.services.sso_client import sso_client
from opentask.services.user_sync_service import sync_or_create_user

logger = logging.getLogger(__name__)


# 不需要认证的路径
EXEMPT_PATHS = {
    "/api/auth/login",
    "/api/auth/logout",
    "/healthcheck",
    "/health",
    "/docs",
    "/redoc",
    "/openapi.json",
}


class SsoAuthMiddleware(BaseHTTPMiddleware):
    """SSO token 认证中间件

    功能：
    1. 从 Authorization header 获取 SSO token
    2. 调用 SSO 接口验证 token 并获取用户信息
    3. 同步/更新本地用户信息
    4. 将本地用户对象注入到 request.state
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # 1. 检查是否跳过认证
        if request.url.path in EXEMPT_PATHS:
            return await call_next(request)

        # 2. 获取 SSO token
        auth_header = request.headers.get("Authorization")
        if not auth_header:
            logger.warning(f"请求缺少认证token: {request.url.path}")
            raise HTTPException(status_code=401, detail="缺少认证token")

        # 3. 调用 SSO 接口验证 token 并获取用户信息
        try:
            sso_user = await sso_client.get_current_user(auth_header)
        except HTTPException as e:
            # SSO token 验证失败
            raise e
        except Exception as e:
            logger.error(f"SSO token 验证异常: {str(e)}")
            raise HTTPException(status_code=500, detail="认证服务异常")

        # 4. 同步/更新本地用户
        try:
            async with AsyncSession() as session:
                local_user = await sync_or_create_user(sso_user, session)

                # 5. 检查用户状态
                if local_user.status != 1:
                    logger.warning(f"用户已被禁用: {local_user.sso_account} (ID: {local_user.id})")
                    raise HTTPException(status_code=403, detail="用户已被禁用，请联系管理员")

                # 6. 将用户对象注入到 request.state
                request.state.user = local_user
                request.state.sso_token = auth_header

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"用户同步失败: {str(e)}")
            raise HTTPException(status_code=500, detail="用户同步失败")

        # 7. 继续处理请求
        response = await call_next(request)
        return response


def get_current_user(request: Request) -> object:
    """
    从 request.state 获取当前用户

    用法：
        from fastapi import Depends, Request
        from opentask.middleware.sso_auth import get_current_user

        @app.get("/api/some-endpoint")
        async def some_endpoint(request: Request, user = Depends(get_current_user)):
            return {"user": user.sso_account}

    Returns:
        UserModel: 当前用户对象

    Raises:
        HTTPException: 用户未认证
    """
    user = getattr(request.state, "user", None)
    if not user:
        raise HTTPException(status_code=401, detail="用户未认证")
    return user
