"""token 端点测试（RFC 6749 §5.2 错误形状 / refresh 轮换与重放）"""

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from opentask.models.oauth2.model import OAuthRefreshToken
from opentask.models.user.model import UserModel
from opentask.services.oauth2.client_service import OAuthClientService
from opentask.services.oauth2.token_service import OAuthTokenService



@pytest.mark.asyncio
async def test_token_endpoint_rejects_bad_secret(
    test_client: AsyncClient, registered_client
):
    """client_secret 错误 → 401 invalid_client"""
    client, _secret = registered_client
    response = await test_client.post(
        "/oauth2/token",
        data={
            "grant_type": "client_credentials",
            "client_id": client.client_id,
            "client_secret": "wrong-secret",
        },
    )
    assert response.status_code == 401
    body = response.json()
    assert body["error"] == "invalid_client"
    assert "error_description" in body


@pytest.mark.asyncio
async def test_token_endpoint_rejects_unsupported_grant_type(
    test_client: AsyncClient, registered_client
):
    """不支持的 grant_type → 400 unsupported_grant_type"""
    client, secret = registered_client
    response = await test_client.post(
        "/oauth2/token",
        data={
            "grant_type": "password",
            "client_id": client.client_id,
            "client_secret": secret,
        },
    )
    assert response.status_code == 400
    assert response.json()["error"] == "unsupported_grant_type"


@pytest.mark.asyncio
async def test_token_endpoint_missing_code_returns_invalid_request(
    test_client: AsyncClient, registered_client
):
    """缺 code → 400 invalid_request"""
    client, secret = registered_client
    response = await test_client.post(
        "/oauth2/token",
        data={
            "grant_type": "authorization_code",
            "client_id": client.client_id,
            "client_secret": secret,
        },
    )
    assert response.status_code == 400
    assert response.json()["error"] == "invalid_request"


@pytest.mark.asyncio
async def test_refresh_token_rotation(
    test_client: AsyncClient, test_session: AsyncSession, oauth_user: UserModel, registered_client
):
    """refresh 轮换：换到新对，旧 refresh 被吊销"""
    client, secret = registered_client
    service = OAuthTokenService(test_session)
    first = await service.issue(
        user=oauth_user, client_id=client.client_id, scope="read:tasks"
    )

    response = await test_client.post(
        "/oauth2/token",
        data={
            "grant_type": "refresh_token",
            "client_id": client.client_id,
            "client_secret": secret,
            "refresh_token": first["refresh_token"],
        },
    )
    assert response.status_code == 200, response.text
    second = response.json()
    assert second["access_token"] != first["access_token"]
    assert second["refresh_token"] != first["refresh_token"]

    # 旧 refresh 行已吊销且记录了轮换链
    result = await test_session.execute(
        select(OAuthRefreshToken).where(
            OAuthRefreshToken.user_id == str(oauth_user.id)
        )
    )
    rows = list(result.scalars().all())
    old = [row for row in rows if row.revoked_at is not None]
    assert old, "旧 refresh 应被吊销"
    assert old[0].rotated_to_hash is not None


@pytest.mark.asyncio
async def test_refresh_replay_revokes_all_tokens(
    test_client: AsyncClient, test_session: AsyncSession, oauth_user: UserModel, registered_client
):
    """refresh 重放（已吊销的再使用）→ invalid_grant 且吊销该用户全部 token"""
    client, secret = registered_client
    service = OAuthTokenService(test_session)
    first = await service.issue(
        user=oauth_user, client_id=client.client_id, scope="read:tasks"
    )

    # 第一次刷新成功（轮换）
    rotate = await test_client.post(
        "/oauth2/token",
        data={
            "grant_type": "refresh_token",
            "client_id": client.client_id,
            "client_secret": secret,
            "refresh_token": first["refresh_token"],
        },
    )
    assert rotate.status_code == 200

    # 重放旧的 refresh → 拒绝
    replay = await test_client.post(
        "/oauth2/token",
        data={
            "grant_type": "refresh_token",
            "client_id": client.client_id,
            "client_secret": secret,
            "refresh_token": first["refresh_token"],
        },
    )
    assert replay.status_code == 400
    assert replay.json()["error"] == "invalid_grant"

    # 重放处置：该用户全部 refresh 被吊销
    result = await test_session.execute(
        select(OAuthRefreshToken).where(
            OAuthRefreshToken.user_id == str(oauth_user.id)
        )
    )
    rows = list(result.scalars().all())
    assert rows
    assert all(row.revoked_at is not None for row in rows)


@pytest.mark.asyncio
async def test_revoke_token_endpoint(
    test_client: AsyncClient, test_session: AsyncSession, oauth_user: UserModel, registered_client
):
    """RFC 7009 吊销：吊销后 access token 立即失效"""
    client, secret = registered_client
    service = OAuthTokenService(test_session)
    pair = await service.issue(
        user=oauth_user, client_id=client.client_id, scope="read:tasks"
    )

    revoke = await test_client.post(
        "/oauth2/revoke",
        json={
            "token": pair["access_token"],
            "client_id": client.client_id,
            "client_secret": secret,
        },
    )
    assert revoke.status_code == 200, revoke.text

    me = await test_client.get(
        "/oauth2/api/me",
        headers={"Authorization": f"Bearer {pair['access_token']}"},
    )
    assert me.status_code == 401


@pytest.mark.asyncio
async def test_revoke_requires_valid_client_secret(
    test_client: AsyncClient, oauth_user: UserModel, registered_client
):
    """吊销端点的 client 凭证错误 → 401"""
    client, _secret = registered_client
    response = await test_client.post(
        "/oauth2/revoke",
        json={
            "token": "whatever",
            "client_id": client.client_id,
            "client_secret": "wrong",
        },
    )
    assert response.status_code == 401
    assert response.json()["error"] == "invalid_client"


@pytest.mark.asyncio
async def test_disabled_client_cannot_exchange_token(
    test_client: AsyncClient, test_session: AsyncSession, oauth_user: UserModel, registered_client
):
    """client 被禁用 → 换 token 拒绝"""
    client, secret = registered_client
    service = OAuthTokenService(test_session)
    pair = await service.issue(
        user=oauth_user, client_id=client.client_id, scope="read:tasks"
    )
    await OAuthClientService(test_session).update(client.client_id, status="DISABLED")

    response = await test_client.post(
        "/oauth2/token",
        data={
            "grant_type": "refresh_token",
            "client_id": client.client_id,
            "client_secret": secret,
            "refresh_token": pair["refresh_token"],
        },
    )
    assert response.status_code == 401
    assert response.json()["error"] == "invalid_client"
