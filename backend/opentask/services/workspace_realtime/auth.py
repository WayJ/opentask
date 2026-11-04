"""Workspace WS 鉴权：token → User；再由路由校验成员。"""

from __future__ import annotations

import logging
from typing import Optional
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from opentask.jwt_utils import verify_token
from opentask.models.user.model import UserModel
from opentask.repositories.base import NotFoundError
from opentask.repositories.user import UserRepository

logger = logging.getLogger(__name__)


def _is_uuid(value: str) -> bool:
    try:
        UUID(value)
        return True
    except (ValueError, AttributeError, TypeError):
        return False


async def resolve_user_from_token(
    token_value: str,
    session: AsyncSession,
) -> UserModel:
    """从 Bearer token（JWT 或 vk_ Access Token）解析用户。

    失败抛 HTTPException 401/403（路由转成 WS close code）。
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
    )
    if not token_value:
        raise credentials_exception

    if token_value.startswith("vk_"):
        from opentask.services.access_token.service import AccessTokenService

        user = await AccessTokenService(session).validate_token(token_value)
        if not user:
            raise credentials_exception
        return user

    try:
        payload = verify_token(token_value)
        sub: Optional[str] = payload.get("sub")
        if sub is None:
            raise credentials_exception
    except HTTPException:
        raise
    except Exception as e:  # noqa: BLE001
        logger.error("WS token validation error: %s", e)
        raise credentials_exception from e

    if payload.get("scp") == "pwd_change":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="请先修改初始密码",
        )

    user_repo = UserRepository()
    user = None
    try:
        if _is_uuid(sub):
            try:
                user = await user_repo.get_by_uuid(session, UUID(sub))
            except NotFoundError:
                user = None
        if user is None:
            user = await user_repo.get_by_username(session, sub)
        if user is None:
            user = await user_repo.get_by_name(session, sub)
    except NotFoundError:
        user = None
    except Exception as e:  # noqa: BLE001
        logger.error("WS user lookup error: %s", e)
        raise credentials_exception from e

    if user is None:
        raise credentials_exception

    token_version = payload.get("tv", 0)
    if token_version != (user.token_version or 0):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="登录态已失效，请重新登录",
        )

    if user.status != 1:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户已被禁用",
        )
    return user
