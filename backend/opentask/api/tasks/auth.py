"""契约层鉴权（S5 D2/D9：复用 access_token 体系，401 语义独立）

两种凭证模式，均走 ``Authorization: Bearer <token>``：
1. bearer_api_key（API Key）：``vk_`` 前缀的用户 Access Token，
   经 AccessTokenService 按哈希校验（models/access_token 现成体系，
   过期/禁用用户自动失效）；
2. oauth2_client_credentials（JWT）：先以 API Key 为 client_secret 调
   ``POST /tasks/token``（grant_type=client_credentials）换短时效 JWT，
   再以该 JWT 访问契约端点（校验链复用 opentask.auth.get_current_user：
   sub 查用户、tv token_version、禁用用户拦截）。

401 语义独立（为 S6 错误规范铺路）：
- 缺凭证 / 凭证无效一律 401（区别于 403/503），错误体带可辨识错误码字段
  ``{"detail": {"code": "CONTRACT_AUTH_*", "message": ...}}``；
- 不复用全局 authenticate（其缺头时是 HTTPBearer 的 403 "Not authenticated"，
  错误体无错误码字段，语义与本契约层不同）。
"""

import logging
from typing import Optional

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from opentask.auth import get_current_user
from opentask.config import config
from opentask.models.user.model import UserModel
from opentask.repositories.base import get_session
from opentask.services.access_token.service import TOKEN_PREFIX, AccessTokenService
from opentask.services.user_center.token_service import TokenService

logger = logging.getLogger(__name__)

# 不自动报错（auto_error=False）：缺头/坏 scheme 由本层统一给 401 + 错误码
_contract_bearer = HTTPBearer(auto_error=False)

# 错误码（S6 错误规范沿用此命名，见 sprint 台账 HC1）
AUTH_CODE_MISSING = "CONTRACT_AUTH_MISSING"  # 未携带凭证
AUTH_CODE_INVALID = "CONTRACT_AUTH_INVALID"  # 凭证错误/过期/吊销/用户禁用
AUTH_CODE_UNSUPPORTED_GRANT = "CONTRACT_AUTH_UNSUPPORTED_GRANT"  # token 端点不支持的花式


def contract_error(status_code: int, code: str, message: str) -> HTTPException:
    """构造契约层错误（错误体含可辨识错误码字段；401 附 WWW-Authenticate）"""
    headers = {"WWW-Authenticate": "Bearer"} if status_code == 401 else None
    return HTTPException(
        status_code=status_code,
        detail={"code": code, "message": message},
        headers=headers,
    )


async def authenticate_contract(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_contract_bearer),
    session: AsyncSession = Depends(get_session),
) -> UserModel:
    """契约层鉴权依赖：API Key（vk_）或 JWT，无效一律 401（带错误码字段）"""
    if credentials is None or not credentials.credentials:
        raise contract_error(
            status.HTTP_401_UNAUTHORIZED,
            AUTH_CODE_MISSING,
            "缺少 Bearer 凭证（Authorization: Bearer <API Key 或 JWT>）",
        )
    if credentials.scheme.lower() != "bearer":
        raise contract_error(
            status.HTTP_401_UNAUTHORIZED,
            AUTH_CODE_MISSING,
            f"Authorization scheme 必须是 Bearer（当前: {credentials.scheme!r}）",
        )

    token = credentials.credentials

    # 模式 1：API Key（vk_ 前缀）—— 哈希查库，过期/禁用用户返回 None
    if token.startswith(TOKEN_PREFIX):
        user = await AccessTokenService(session).validate_token(token)
        if user is None:
            raise contract_error(
                status.HTTP_401_UNAUTHORIZED,
                AUTH_CODE_INVALID,
                "API Key 无效、已过期或用户被禁用",
            )
        return user

    # 模式 2：JWT（client credentials 端点签发 / 用户登录态）——
    # 复用全局校验链（sub 查用户、tv 版本、禁用拦截），异常统一收敛为契约层 401
    try:
        return await get_current_user(request, credentials, session)
    except HTTPException as e:
        logger.info("契约层 JWT 校验失败: %s", e.detail)
        raise contract_error(
            status.HTTP_401_UNAUTHORIZED,
            AUTH_CODE_INVALID,
            "JWT 无效、已过期或权限不足",
        ) from e


async def exchange_client_credentials(
    session: AsyncSession,
    *,
    grant_type: Optional[str],
    client_id: Optional[str],
    client_secret: Optional[str],
    user_agent: Optional[str] = None,
    ip: Optional[str] = None,
) -> dict:
    """OAuth2 client credentials 换 token：API Key → 短时效 JWT

    凭证映射（D9 复用 access_token 体系）：
    - client_secret：必填，``vk_`` API Key（AccessTokenService 校验）
    - client_id：可选，提供时须与该 Key 归属用户 ID 一致（双重校验）

    返回 OAuth2 形状 ``{access_token, token_type, expires_in}``；
    按 RFC 6749 §4.4.3 client_credentials 不下发 refresh_token。
    """
    if grant_type != "client_credentials":
        raise contract_error(
            status.HTTP_400_BAD_REQUEST,
            AUTH_CODE_UNSUPPORTED_GRANT,
            f"仅支持 grant_type=client_credentials（当前: {grant_type!r}）",
        )
    if not client_secret:
        raise contract_error(
            status.HTTP_401_UNAUTHORIZED,
            AUTH_CODE_MISSING,
            "缺少 client_secret（API Key，vk_ 前缀）",
        )

    user = await AccessTokenService(session).validate_token(client_secret)
    if user is None:
        raise contract_error(
            status.HTTP_401_UNAUTHORIZED,
            AUTH_CODE_INVALID,
            "client_secret 无效、已过期或用户被禁用",
        )
    if client_id and client_id != str(user.id):
        raise contract_error(
            status.HTTP_401_UNAUTHORIZED,
            AUTH_CODE_INVALID,
            "client_id 与 client_secret 归属用户不一致",
        )

    pair = await TokenService(session).issue_tokens(
        user, user_agent=user_agent, ip=ip
    )
    return {
        "access_token": pair["token"],
        "token_type": "Bearer",
        "expires_in": config.access_expire_minutes * 60,
    }
