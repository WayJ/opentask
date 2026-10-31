"""Jira 线格式鉴权：Basic / Bearer → 契约 access_token 内核

探测报告 §1/§5：Orca server 模式站点每请求携带

- ``Authorization: Basic base64(username:token)``（连接表单 email+token），或
- ``Authorization: Bearer <PAT>``（无 username 的 PAT 模式）

两种头提取出的 token 统一交给契约凭证解析内核
``opentask.api.tasks.auth.resolve_contract_token``（vk_ API Key 或 JWT →
用户），不复制校验业务。Basic 的 username 位不参与校验（OpenTask 凭证即
token 本身，username 仅作展示提示）。
"""

import base64
import binascii
import logging
from typing import Optional

from fastapi import Depends, Request
from fastapi.exceptions import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from opentask.api.tasks.auth import resolve_contract_token
from opentask.api.tasks.errors import get_contract_session
from opentask.models.user.model import UserModel

from .errors import jira_auth_invalid, jira_auth_missing, jira_unavailable

logger = logging.getLogger(__name__)


async def get_jira_session(
    session: AsyncSession = Depends(get_contract_session),
) -> AsyncSession:
    """Jira 线会话依赖：复用契约层可用性探测，503 换 Jira 形状错误体"""
    return session


async def authenticate_jira(
    request: Request,
    session: AsyncSession = Depends(get_jira_session),
) -> UserModel:
    """Jira 线鉴权依赖：解析 Basic/Bearer 头 → 契约凭证内核 → 用户

    依赖不可达（503）先于 401（与 tasks 契约层同序）。
    """
    header = request.headers.get("authorization") or ""
    scheme, _, param = header.partition(" ")
    scheme = scheme.strip().lower()
    param = param.strip()

    token: Optional[str] = None
    if scheme == "basic":
        try:
            decoded = base64.b64decode(param, validate=True).decode("utf-8")
        except (binascii.Error, UnicodeDecodeError, ValueError):
            raise jira_auth_missing("Basic 凭证不是合法的 base64(user:token)")
        _username, _, password = decoded.partition(":")
        token = password or None
    elif scheme == "bearer":
        token = param or None
    elif header:
        raise jira_auth_missing(
            f"Authorization scheme 必须是 Basic 或 Bearer（当前: {scheme!r}）"
        )

    if not token:
        raise jira_auth_missing(
            "缺少凭证（Authorization: Basic base64(user:API Key) 或 Bearer <API Key/JWT>）"
        )

    try:
        user = await resolve_contract_token(request, token, session)
    except HTTPException as e:
        # 内核仅对数据库不可达抛 HTTPException（503）；凭证类问题返回 None
        logger.warning("Jira 线凭证解析异常: %s", e.detail)
        raise jira_unavailable("后端依赖不可达（数据库连接失败），请稍后重试") from e
    if user is None:
        raise jira_auth_invalid("凭证无效、已过期或用户被禁用（API Key 或 JWT）")
    return user
