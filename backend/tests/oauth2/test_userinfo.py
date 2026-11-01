"""userinfo 端点与身份对齐测试（G1：email 作 username 种子建号）"""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from opentask.models.user.model import UserModel
from opentask.services.oauth2.identity_service import OAuthIdentityService
from opentask.services.oauth2.token_service import OAuthTokenService



@pytest.mark.asyncio
async def test_userinfo_shape(
    test_client: AsyncClient, test_session: AsyncSession, oauth_user: UserModel, registered_client
):
    """userinfo 返回 sub/username/name"""
    client, _secret = registered_client
    pair = await OAuthTokenService(test_session).issue(
        user=oauth_user, client_id=client.client_id, scope="profile"
    )
    response = await test_client.get(
        "/oauth2/userinfo",
        headers={"Authorization": f"Bearer {pair['access_token']}"},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["sub"] == str(oauth_user.id)
    assert body["username"] == oauth_user.username


@pytest.mark.asyncio
async def test_userinfo_requires_profile_scope(
    test_client: AsyncClient, test_session: AsyncSession, oauth_user: UserModel, registered_client
):
    """缺 profile scope → 403"""
    client, _secret = registered_client
    pair = await OAuthTokenService(test_session).issue(
        user=oauth_user, client_id=client.client_id, scope="read:tasks"
    )
    response = await test_client.get(
        "/oauth2/userinfo",
        headers={"Authorization": f"Bearer {pair['access_token']}"},
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_identity_reuses_existing_user(test_session: AsyncSession):
    """email 命中既有 username → 复用，不新建"""
    service = OAuthIdentityService(test_session)
    existing = UserModel(
        name="已有用户",
        username="existing@example.com",
        password_hash=None,
        role="viewer",
        status=1,
    )
    test_session.add(existing)
    await test_session.commit()
    await test_session.refresh(existing)

    user, created = await service.resolve_or_create(
        email="existing@example.com", display_name="已有用户"
    )
    assert created is False
    assert user.id == existing.id


@pytest.mark.asyncio
async def test_identity_creates_user_with_email_seeded_username(
    test_session: AsyncSession,
):
    """email 未命中 → 建号：username = email，name = 展示名，role=viewer"""
    service = OAuthIdentityService(test_session)
    user, created = await service.resolve_or_create(
        email="New.User@Example.com", display_name="新用户"
    )
    assert created is True
    assert user.username == "new.user@example.com"
    assert user.name == "新用户"
    assert user.role == "viewer"
    assert user.password_hash is None


@pytest.mark.asyncio
async def test_identity_uniques_conflicting_username(test_session: AsyncSession):
    """username 冲突 → 追加序号（unique_username）"""
    # 占位用户的 **name** 恰为 "dup@example.com"（username 精确查不到，
    # 但 unique_username 的归一化基准含 name → 触发序号后缀）
    first = UserModel(
        name="dup@example.com",
        username="occupied_holder",
        password_hash=None,
        role="viewer",
        status=1,
    )
    test_session.add(first)
    await test_session.commit()

    service = OAuthIdentityService(test_session)
    user, created = await service.resolve_or_create(
        email="dup@example.com", display_name="第二用户"
    )
    assert created is True
    assert user.username == "dup@example.com_2"


@pytest.mark.asyncio
async def test_identity_requires_email(test_session: AsyncSession):
    """缺 email → ValueError"""
    service = OAuthIdentityService(test_session)
    with pytest.raises(ValueError):
        await service.resolve_or_create(email="", display_name="x")
