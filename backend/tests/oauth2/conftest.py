"""OAuth2 Provider 测试共用 fixture

提供：
- ``oauth_user``：启用状态的真实用户（token 校验需要 sub/tv/status）；
- ``registered_client``：注册好的 OAuth client（含明文 secret，仅此一次）；
- ``admin_user``：管理端点用的 admin 身份。

**隔离约定**：本仓 conftest 的清理只删 Task 行，用户/令牌行会跨用例残留。
因此本目录所有 fixture 的 username / client_id 均带**每用例唯一后缀**，
避免撞 `uq_user_username` / `ix_oauth_clients_client_id` 唯一索引。
"""

import uuid

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from opentask.models.user.model import UserModel
from opentask.services.oauth2.client_service import OAuthClientService

# 常用 scope 集合
READ_SCOPES = ["read:tasks", "read:projects", "read:requirements", "profile"]
REDIRECT_URI = "https://dsh.example.com/enterprise/api/v1/app-oauth/opentask/callback"


def unique_suffix() -> str:
    """每用例唯一后缀（8 位十六进制）"""
    return uuid.uuid4().hex[:8]


@pytest_asyncio.fixture
async def oauth_user(test_session: AsyncSession) -> UserModel:
    """启用状态的 OAuth 用户（status=1，token_version=0）"""
    suffix = unique_suffix()
    user = UserModel(
        name=f"OAuth 测试用户 {suffix}",
        username=f"oauth_test_{suffix}",
        password_hash=None,
        role="viewer",
        status=1,
    )
    test_session.add(user)
    await test_session.commit()
    await test_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def admin_user(test_session: AsyncSession) -> UserModel:
    """管理员用户（管理端点需要 admin 角色）"""
    suffix = unique_suffix()
    user = UserModel(
        name=f"OAuth 管理员 {suffix}",
        username=f"oauth_admin_{suffix}",
        password_hash=None,
        role="admin",
        status=1,
    )
    test_session.add(user)
    await test_session.commit()
    await test_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def registered_client(test_session: AsyncSession, oauth_user: UserModel):
    """注册好的 OAuth client，返回 (client, secret_plain)"""
    client, secret = await OAuthClientService(test_session).register(
        client_id=f"dsh-saas-{unique_suffix()}",
        name="dsh-saas 工作台",
        description="小蓝 CoWork 管理后台",
        redirect_uris=[REDIRECT_URI],
        scopes=READ_SCOPES,
        created_by=str(oauth_user.id),
    )
    return client, secret
