"""OAuth2 授权码流程测试（签发 → 消费 → 重放处置）"""

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from opentask.jwt_utils import create_access_token
from opentask.models.oauth2.model import OAuthAccessToken
from opentask.models.user.model import UserModel
from opentask.services.oauth2.authorization_service import AuthorizationCodeService
from opentask.services.oauth2.client_service import OAuthClientService

from .conftest import READ_SCOPES, REDIRECT_URI


def _bearer(user: UserModel) -> dict:
    token = create_access_token({"sub": str(user.id), "tv": user.token_version})
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_authorize_context_returns_client_info(
    test_client: AsyncClient, oauth_user: UserModel, registered_client
):
    """同意页上下文 → 返回应用名/描述/scope 清单/回调主机"""
    client, _secret = registered_client
    response = await test_client.get(
        "/api/oauth2/authorize/context",
        params={
            "client_id": client.client_id,
            "redirect_uri": REDIRECT_URI,
            "response_type": "code",
            "scope": "read:tasks profile",
            "state": "st-123",
        },
        headers=_bearer(oauth_user),
    )
    assert response.status_code == 200, response.text
    body = response.json()["data"]
    assert body["client_name"] == "dsh-saas 工作台"
    assert body["client_description"] == "小蓝 CoWork 管理后台"
    assert body["scope"] == ["profile", "read:tasks"]
    assert body["redirect_host"] == "dsh.example.com"
    assert body["state"] == "st-123"


@pytest.mark.asyncio
async def test_authorize_context_rejects_bad_redirect_uri(
    test_client: AsyncClient, oauth_user: UserModel, registered_client
):
    """redirect_uri 不在白名单 → 400 invalid_redirect_uri（**不重定向**）"""
    client, _secret = registered_client
    response = await test_client.get(
        "/api/oauth2/authorize/context",
        params={
            "client_id": client.client_id,
            "redirect_uri": "https://evil.example.com/steal",
            "scope": "read:tasks",
        },
        headers=_bearer(oauth_user),
    )
    assert response.status_code == 400
    assert response.json()["detail"]["error"] == "invalid_redirect_uri"


@pytest.mark.asyncio
async def test_authorize_context_rejects_scope_beyond_allowed(
    test_client: AsyncClient, oauth_user: UserModel, registered_client
):
    """请求 scope 超出 client 允许集 → 400 invalid_scope"""
    client, _secret = registered_client
    response = await test_client.get(
        "/api/oauth2/authorize/context",
        params={
            "client_id": client.client_id,
            "redirect_uri": REDIRECT_URI,
            "scope": "read:tasks admin:all",
        },
        headers=_bearer(oauth_user),
    )
    assert response.status_code == 400
    detail = response.json()["detail"]
    assert detail["error"] == "invalid_scope"
    assert "admin:all" in detail["error_description"]


@pytest.mark.asyncio
async def test_deny_returns_access_denied_redirect(
    test_client: AsyncClient, oauth_user: UserModel, registered_client
):
    """拒绝授权 → 跳转 URL 带 error=access_denied 与 state"""
    client, _secret = registered_client
    response = await test_client.post(
        "/api/oauth2/authorize/approve",
        json={
            "client_id": client.client_id,
            "redirect_uri": REDIRECT_URI,
            "scope": "read:tasks",
            "state": "st-deny",
            "decision": "deny",
        },
        headers=_bearer(oauth_user),
    )
    assert response.status_code == 200, response.text
    redirect_to = response.json()["data"]["redirect_to"]
    assert "error=access_denied" in redirect_to
    assert "state=st-deny" in redirect_to


@pytest.mark.asyncio
async def test_full_authorization_code_flow(
    test_client: AsyncClient, oauth_user: UserModel, registered_client
):
    """完整链路：同意 → code → 换 token → access token 可用"""
    client, secret = registered_client
    approve = await test_client.post(
        "/api/oauth2/authorize/approve",
        json={
            "client_id": client.client_id,
            "redirect_uri": REDIRECT_URI,
            "scope": "read:tasks profile",
            "state": "st-ok",
            "decision": "approve",
        },
        headers=_bearer(oauth_user),
    )
    assert approve.status_code == 200, approve.text
    redirect_to = approve.json()["data"]["redirect_to"]
    assert "code=" in redirect_to
    assert "state=st-ok" in redirect_to
    code = redirect_to.split("code=")[1].split("&")[0]

    token_response = await test_client.post(
        "/oauth2/token",
        data={
            "grant_type": "authorization_code",
            "client_id": client.client_id,
            "client_secret": secret,
            "code": code,
            "redirect_uri": REDIRECT_URI,
        },
    )
    assert token_response.status_code == 200, token_response.text
    body = token_response.json()
    assert body["token_type"] == "Bearer"
    assert body["expires_in"] > 0
    assert body["refresh_token"]
    assert "read:tasks" in body["scope"]

    # access token 可用于只读数据面
    me = await test_client.get(
        "/oauth2/api/me",
        headers={"Authorization": f"Bearer {body['access_token']}"},
    )
    assert me.status_code == 200, me.text
    assert me.json()["sub"] == str(oauth_user.id)


@pytest.mark.asyncio
async def test_authorization_code_is_single_use_and_replay_revokes_all(
    test_client: AsyncClient, test_session: AsyncSession, oauth_user: UserModel, registered_client
):
    """授权码一次性；**重放 → 吊销该用户全部 OAuth 令牌**"""
    client, secret = registered_client
    approve = await test_client.post(
        "/api/oauth2/authorize/approve",
        json={
            "client_id": client.client_id,
            "redirect_uri": REDIRECT_URI,
            "scope": "read:tasks",
            "decision": "approve",
        },
        headers=_bearer(oauth_user),
    )
    code = approve.json()["data"]["redirect_to"].split("code=")[1].split("&")[0]

    first = await test_client.post(
        "/oauth2/token",
        data={
            "grant_type": "authorization_code",
            "client_id": client.client_id,
            "client_secret": secret,
            "code": code,
        },
    )
    assert first.status_code == 200, first.text
    access_token = first.json()["access_token"]

    # 重放同一授权码 → invalid_grant
    replay = await test_client.post(
        "/oauth2/token",
        data={
            "grant_type": "authorization_code",
            "client_id": client.client_id,
            "client_secret": secret,
            "code": code,
        },
    )
    assert replay.status_code == 400
    assert replay.json()["error"] == "invalid_grant"

    # 重放处置：该用户全部 OAuth access token 已被吊销
    result = await test_session.execute(
        select(OAuthAccessToken).where(OAuthAccessToken.user_id == str(oauth_user.id))
    )
    rows = list(result.scalars().all())
    assert rows, "应有已签发的 access token 行"
    assert all(row.revoked_at is not None for row in rows), "重放后全部 token 应被吊销"

    # 被吊销的 access token 不再可用
    me = await test_client.get(
        "/oauth2/api/me",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert me.status_code == 401


@pytest.mark.asyncio
async def test_expired_authorization_code_rejected(
    test_client: AsyncClient, test_session: AsyncSession, oauth_user: UserModel, registered_client
):
    """过期授权码 → invalid_grant"""
    client, secret = registered_client
    code_service = AuthorizationCodeService(test_session)
    code = await code_service.issue(
        client_id=client.client_id,
        user_id=str(oauth_user.id),
        redirect_uri=REDIRECT_URI,
        scope="read:tasks",
    )
    # 手动把过期时间推到过去
    from datetime import datetime, timedelta

    record = await code_service.find(code)
    record.expires_at = datetime.utcnow() - timedelta(seconds=1)
    await test_session.commit()

    response = await test_client.post(
        "/oauth2/token",
        data={
            "grant_type": "authorization_code",
            "client_id": client.client_id,
            "client_secret": secret,
            "code": code,
        },
    )
    assert response.status_code == 400
    assert response.json()["error"] == "invalid_grant"


@pytest.mark.asyncio
async def test_code_cannot_be_used_by_other_client(
    test_client: AsyncClient, test_session: AsyncSession, oauth_user: UserModel, registered_client
):
    """授权码不能被另一个 client 消费"""
    client, _secret = registered_client
    other_client, other_secret = await OAuthClientService(test_session).register(
        client_id="other-client",
        name="另一个应用",
        description=None,
        redirect_uris=[REDIRECT_URI],
        scopes=READ_SCOPES,
        created_by=str(oauth_user.id),
    )
    code_service = AuthorizationCodeService(test_session)
    code = await code_service.issue(
        client_id=client.client_id,
        user_id=str(oauth_user.id),
        redirect_uri=REDIRECT_URI,
        scope="read:tasks",
    )

    response = await test_client.post(
        "/oauth2/token",
        data={
            "grant_type": "authorization_code",
            "client_id": other_client.client_id,
            "client_secret": other_secret,
            "code": code,
        },
    )
    assert response.status_code == 400
    assert response.json()["error"] == "invalid_grant"
