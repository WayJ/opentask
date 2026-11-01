"""OAuth2 client 注册管理测试"""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from opentask.jwt_utils import create_access_token
from opentask.models.user.model import UserModel
from opentask.services.oauth2.client_service import OAuthClientService

from .conftest import READ_SCOPES, REDIRECT_URI


def _admin_bearer(admin_user: UserModel) -> dict:
    token = create_access_token({"sub": str(admin_user.id), "tv": admin_user.token_version})
    return {"Authorization": f"Bearer {token}"}


def _viewer_bearer(user: UserModel) -> dict:
    token = create_access_token({"sub": str(user.id), "tv": user.token_version})
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_register_client_returns_secret_once(
    test_client: AsyncClient, admin_user: UserModel
):
    """注册 client → secret 明文仅此一次返回"""
    response = await test_client.post(
        "/api/oauth2/clients",
        json={
            "client_id": "crud-client-1",
            "name": "注册测试应用",
            "description": "描述",
            "redirect_uris": [REDIRECT_URI],
            "scopes": READ_SCOPES,
        },
        headers=_admin_bearer(admin_user),
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["client"]["client_id"] == "crud-client-1"
    assert body["client_secret"].startswith("ocs_")
    assert body["client"]["secret_prefix"].startswith("ocs_")

    # 列表不得含 secret 明文（只允许展示前缀）
    listing = await test_client.get(
        "/api/oauth2/clients", headers=_admin_bearer(admin_user)
    )
    assert listing.status_code == 200
    assert "client_secret" not in listing.text
    assert body["client_secret"] not in listing.text
    assert body["client"]["secret_prefix"] in listing.text


@pytest.mark.asyncio
async def test_register_client_requires_admin(test_client: AsyncClient, oauth_user: UserModel):
    """非 admin 注册 client → 403"""
    response = await test_client.post(
        "/api/oauth2/clients",
        json={
            "client_id": "crud-client-2",
            "name": "越权应用",
            "redirect_uris": [REDIRECT_URI],
            "scopes": READ_SCOPES,
        },
        headers=_viewer_bearer(oauth_user),
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_register_duplicate_client_id_fails(
    test_client: AsyncClient, admin_user: UserModel
):
    """重复 client_id → 400"""
    payload = {
        "client_id": "crud-client-dup",
        "name": "重复应用",
        "redirect_uris": [REDIRECT_URI],
        "scopes": READ_SCOPES,
    }
    headers = _admin_bearer(admin_user)
    first = await test_client.post("/api/oauth2/clients", json=payload, headers=headers)
    assert first.status_code == 200
    second = await test_client.post("/api/oauth2/clients", json=payload, headers=headers)
    assert second.status_code == 400


@pytest.mark.asyncio
async def test_rotate_secret_changes_hash(test_session: AsyncSession, admin_user: UserModel):
    """轮换 secret → 哈希变化，旧 secret 失效"""
    service = OAuthClientService(test_session)
    client, old_secret = await service.register(
        client_id="crud-rotate",
        name="轮换测试",
        description=None,
        redirect_uris=[REDIRECT_URI],
        scopes=READ_SCOPES,
        created_by=str(admin_user.id),
    )
    old_hash = client.client_secret_hash
    _client, new_secret = await service.rotate_secret("crud-rotate")
    assert new_secret != old_secret
    assert client.client_secret_hash != old_hash

    # 旧 secret 校验失败，新 secret 通过
    with pytest.raises(Exception):
        service.verify_secret(client, old_secret)
    service.verify_secret(client, new_secret)


@pytest.mark.asyncio
async def test_disabled_client_cannot_authorize(test_session: AsyncSession, admin_user: UserModel):
    """禁用 client → 授权请求被拒"""
    service = OAuthClientService(test_session)
    client, _secret = await service.register(
        client_id="crud-disabled",
        name="禁用测试",
        description=None,
        redirect_uris=[REDIRECT_URI],
        scopes=READ_SCOPES,
        created_by=str(admin_user.id),
    )
    await service.update("crud-disabled", status="DISABLED")
    with pytest.raises(Exception):
        await service.require_active_client("crud-disabled")


@pytest.mark.asyncio
async def test_unknown_client_rejected(test_session: AsyncSession):
    """未知 client → ClientNotFoundError"""
    service = OAuthClientService(test_session)
    with pytest.raises(Exception):
        await service.require_active_client("never-registered-client")
