"""OAuth2 依赖（令牌校验内核 + 作用域守卫）

**作用域强制口径**（见 docs/superpowers/specs/2026-11-02-oauth2-provider-design.md）：

python-jose 3.5.0 在 ``jwt.decode`` 不传 ``audience=`` 时，对带 ``aud`` claim 的
token 直接抛 ``JWTError: Invalid audience``。既有 ``jwt_utils.verify_token``
正是这种调用，故带 ``aud`` 的 OAuth access token 天然进不了全局鉴权链
（``/api/*``）与契约层（``/tasks``）——只读 scope 形同虚设的风险为零，
既有 ``auth.py`` / ``jwt_utils.py`` 零改动。

OAuth 侧则显式解码（``verify_aud=False``）+ 自行比对 ``aud``，再校验 scope。
该库行为由 ``backend/tests/oauth2/test_scope_enforcement.py`` 钉死为回归测试。
"""

from typing import Optional

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from .metadata import mcp_challenge
from opentask.models.user.model import UserModel
from opentask.repositories.base import get_session
from opentask.services.oauth2.token_service import (
    InsufficientScopeError,
    InvalidTokenError,
    OAuthTokenService,
    ReplayDetectedError,
    TokenRevokedError,
)

# 不自动报错：缺头/坏 scheme 由本层统一给 401
_oauth_bearer = HTTPBearer(auto_error=False)


async def get_oauth_session(session: AsyncSession = Depends(get_session)) -> AsyncSession:
    """OAuth 层会话依赖"""
    return session


async def require_oauth_token(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_oauth_bearer),
    session: AsyncSession = Depends(get_oauth_session),
) -> tuple[dict, UserModel]:
    """校验 OAuth access token，返回 (payload, 用户)

    失败一律 401（缺凭证 / 无效 / 已吊销 / 用户禁用 / token_version 失效）。
    """
    def challenge() -> str:
        if request.url.path != "/mcp":
            return "Bearer"
        try:
            return mcp_challenge()
        except HTTPException:
            return "Bearer"
    if credentials is None or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="缺少访问令牌",
            headers={"WWW-Authenticate": challenge()},
        )
    service = OAuthTokenService(session)
    try:
        return await service.verify(token=credentials.credentials)
    except (InvalidTokenError, TokenRevokedError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
            headers={"WWW-Authenticate": challenge()},
        )
    except ReplayDetectedError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
            headers={"WWW-Authenticate": challenge()},
        )


def require_oauth_scope(*required: str):
    """生成「要求指定 scope」的依赖

    scope 不足 → **403 insufficient_scope**（RFC 6750 §3.1），
    令牌本身无效仍走 401。
    """

    async def _dependency(
        payload_and_user: tuple[dict, UserModel] = Depends(require_oauth_token),
    ) -> tuple[dict, UserModel]:
        payload, user = payload_and_user
        # Resource-bound MCP tokens are valid only at their declared resource.
        if payload.get("client_id") and payload.get("aud") != payload.get("client_id"):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="令牌不适用于此资源",
                headers={"WWW-Authenticate": 'Bearer error="invalid_token"'},
            )
        granted = set((payload.get("scope") or "").split())
        missing = [item for item in required if item not in granted]
        if missing:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error": "insufficient_scope",
                    "error_description": f"缺少所需权限: {' '.join(missing)}",
                },
                headers={
                    "WWW-Authenticate": (
                        f'Bearer error="insufficient_scope", scope="{" ".join(required)}"'
                    )
                },
            )
        return payload, user

    return _dependency
