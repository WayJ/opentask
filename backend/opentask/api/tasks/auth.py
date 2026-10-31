"""契约层鉴权（S5 D2/D9：复用 access_token 体系，401 语义独立）

两种凭证模式，均走 ``Authorization: Bearer <token>``：
1. bearer_api_key（API Key）：``vk_`` 前缀的用户 Access Token，
   经 AccessTokenService 按哈希校验（models/access_token 现成体系，
   过期/禁用用户自动失效）；
2. oauth2_client_credentials（JWT）：先以 API Key 为 client_secret 调
   ``POST /tasks/token``（grant_type=client_credentials）换短时效 JWT，
   再以该 JWT 访问契约端点（校验链复用 opentask.auth.get_current_user：
   sub 查用户、tv token_version、禁用用户拦截）。

401 语义独立（S5 落地，S6 定稿于 errors.py）：
- 缺凭证 / 凭证无效一律 401（区别于 403/503），错误体带可辨识错误码字段
  ``{"detail": {"code": "CONTRACT_AUTH_*", "message": ...}}``；
- 不复用全局 authenticate（其缺头时是 HTTPBearer 的 403 "Not authenticated"，
  错误体无错误码字段，语义与本契约层不同）。

会话经 get_contract_session（S6）：依赖不可达时先于凭证校验返回
503 CONTRACT_UNAVAILABLE（凭证无法在依赖不可达时验证）。
"""

import logging
from typing import Optional

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from opentask.auth import get_current_user
from opentask.config import config
from opentask.jwt_utils import create_access_token
from opentask.models.user.model import UserModel
from opentask.services.access_token.service import TOKEN_PREFIX, AccessTokenService

from .errors import (
    AUTH_CODE_INVALID,
    AUTH_CODE_MISSING,
    AUTH_CODE_UNSUPPORTED_GRANT,
    contract_error,
    get_contract_session,
)

logger = logging.getLogger(__name__)

# 不自动报错（auto_error=False）：缺头/坏 scheme 由本层统一给 401 + 错误码
_contract_bearer = HTTPBearer(auto_error=False)


async def authenticate_contract(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_contract_bearer),
    session: AsyncSession = Depends(get_contract_session),
) -> UserModel:
    """契约层鉴权依赖：API Key（vk_）或 JWT，无效一律 401（带错误码字段）

    会话先经 get_contract_session 探测可用性：依赖不可达 → 503（先于 401）。
    """
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
) -> dict:
    """OAuth2 client credentials 换 token：API Key → 短时效 access JWT

    凭证映射（D9 复用 access_token 体系）：
    - client_secret：必填，``vk_`` API Key（AccessTokenService 校验）
    - client_id：可选，提供时须与该 Key 归属用户 ID 一致（双重校验）

    返回 OAuth2 形状 ``{access_token, token_type, expires_in}``：
    - 按 RFC 6749 §4.4.3 client_credentials 不下发 refresh_token，
      也不落 refresh_tokens 行（无孤儿数据）；
    - 直签无 scp 声明的 JWT（无限制用途；API Key bearer 模式同权，
      交换不降权——见函数尾注释）。
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

    # 直签无 scp 的 access JWT（不经 TokenService.issue_tokens）：
    # - RFC 6749 §4.4.3 client_credentials 不下发 refresh token，因此也不
    #   落 refresh_tokens 行（issue_tokens 固定签对，交换路径丢弃明文即成
    #   孤儿行，累积无回收）；
    # - 显式无限制 scope：issue_tokens 未显式传 scope 时，对
    #   must_change_password 用户会继承 scp=pwd_change 受限 token，用于
    #   契约端点会被全局校验链拒绝（并被误折叠成 401 INVALID）。API Key
    #   本身即完整凭证（bearer 模式同权直接放行），token 交换只是形态转换，
    #   不应降权。
    access = create_access_token({"sub": str(user.id), "tv": user.token_version})
    return {
        "access_token": access,
        "token_type": "Bearer",
        "expires_in": config.access_expire_minutes * 60,
    }