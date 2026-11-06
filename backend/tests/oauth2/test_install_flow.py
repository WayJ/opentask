"""OAuth 自动接入（Install Flow）测试

协议契约：docs/superpowers/contracts/2026-11-06-e101-oauth2-install-contract.md

覆盖（对照设计 §5）：
发起幂等/冲突/配额 → 批准（管理员门禁、幂等保护）→ 回跳带 code&state →
兑换（verifier 绑定、单次消费、密钥只存哈希）→ 恢复窗口（换发新密钥 / 窗口外失败）
→ 状态查询（verifier 鉴权）→ 内容精确绑定 → callback 主机绑定 → 日志不泄密。
"""

import base64
import hashlib
import json
import secrets

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from opentask.jwt_utils import create_access_token
from opentask.models.oauth2.model import OAuthClient, OAuthInstallRequest
from opentask.models.user.model import UserModel

from .conftest import READ_SCOPES, REDIRECT_URI

CALLBACK_URL = "https://dsh.example.com/enterprise/install/done"


@pytest.fixture(autouse=True)
def _relax_rate_limit(monkeypatch):
    """放宽单 IP 创建速率上限（连续用例共享同一 testclient IP；限流语义由专属用例覆盖）"""
    from opentask.config import config

    monkeypatch.setattr(
        type(config), "oauth_install_rate_limit_per_minute", property(lambda self: 1000)
    )
    monkeypatch.setattr(
        type(config), "oauth_install_max_pending_per_ip", property(lambda self: 1000)
    )



def _s256(verifier: str) -> str:
    return base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()


def _admin_bearer(admin_user: UserModel) -> dict:
    token = create_access_token({"sub": str(admin_user.id), "tv": admin_user.token_version})
    return {"Authorization": f"Bearer {token}"}


def _viewer_bearer(user: UserModel) -> dict:
    token = create_access_token({"sub": str(user.id), "tv": user.token_version})
    return {"Authorization": f"Bearer {token}"}


def _payload(client_id: str, verifier: str, **overrides) -> dict:
    payload = {
        "client_id": client_id,
        "name": "小蓝 CoWork",
        "description": "小蓝 CoWork 管理后台",
        "redirect_uris": [REDIRECT_URI],
        "scopes": list(READ_SCOPES),
        "callback_url": CALLBACK_URL,
        "state": "state-abc-123",
        "code_challenge": _s256(verifier),
        "code_challenge_method": "S256",
    }
    payload.update(overrides)
    return payload


async def _create_request(
    test_client: AsyncClient, client_id: str, verifier: str, **overrides
) -> dict:
    response = await test_client.post(
        "/api/oauth2/install/requests", json=_payload(client_id, verifier, **overrides)
    )
    assert response.status_code in (200, 201), response.text
    return response.json()["data"]


async def _approve(
    test_client: AsyncClient, install_id: str, admin_user: UserModel
) -> dict:
    response = await test_client.post(
        f"/api/oauth2/install/requests/{install_id}/approve",
        headers=_admin_bearer(admin_user),
        json={"approved": True},
    )
    assert response.status_code == 200, response.text
    return response.json()["data"]


# ===== 发起申请 =====


@pytest.mark.asyncio
async def test_create_request_returns_pending_and_approval_url(test_client: AsyncClient):
    """发起申请 → pending + approval_url + 相对路径"""
    verifier = secrets.token_urlsafe(32)
    data = await _create_request(test_client, "install-client-1", verifier)

    assert data["status"] == "PENDING"
    assert data["install_id"]
    assert data["approval_path"] == f"/oauth2/install/{data['install_id']}"
    assert data["approval_url"].endswith(data["approval_path"])
    assert data["reused"] is False


@pytest.mark.asyncio
async def test_create_request_is_idempotent_for_same_client_and_challenge(test_client: AsyncClient):
    """同 client_id + 同 challenge 重复发起 → 复用同一 install_id"""
    verifier = secrets.token_urlsafe(32)
    first = await _create_request(test_client, "install-client-idem", verifier)
    second = await _create_request(test_client, "install-client-idem", verifier)

    assert second["install_id"] == first["install_id"]
    assert second["reused"] is True


@pytest.mark.asyncio
async def test_create_request_rejects_plain_challenge_method(test_client: AsyncClient):
    """code_challenge_method=plain → 422（防降级）"""
    verifier = secrets.token_urlsafe(32)
    response = await test_client.post(
        "/api/oauth2/install/requests",
        json=_payload("install-client-plain", verifier, code_challenge_method="plain"),
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_create_request_rejects_malformed_challenge(test_client: AsyncClient):
    """challenge 长度/字符集非法 → 422"""
    response = await test_client.post(
        "/api/oauth2/install/requests",
        json=_payload("install-client-bad-challenge", "x", code_challenge="short"),
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_create_request_rejects_callback_host_not_bound(test_client: AsyncClient):
    """callback_url 主机不在 redirect_uris 主机集合 → 422（开放重定向缓解 M2）"""
    verifier = secrets.token_urlsafe(32)
    response = await test_client.post(
        "/api/oauth2/install/requests",
        json=_payload(
            "install-client-openredirect",
            verifier,
            callback_url="https://evil.example.net/steal",
        ),
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_create_request_rejects_non_absolute_redirect_uri(test_client: AsyncClient):
    """redirect_uri 非绝对 URL → 422"""
    verifier = secrets.token_urlsafe(32)
    response = await test_client.post(
        "/api/oauth2/install/requests",
        json=_payload(
            "install-client-reluri", verifier, redirect_uris=["/relative/callback"]
        ),
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_create_request_conflicts_with_existing_client(
    test_client: AsyncClient, admin_user: UserModel
):
    """client_id 与既有正式 client 冲突 → 409"""
    existing = await test_client.post(
        "/api/oauth2/clients",
        json={
            "client_id": "install-client-conflict",
            "name": "既有应用",
            "redirect_uris": [REDIRECT_URI],
            "scopes": READ_SCOPES,
        },
        headers=_admin_bearer(admin_user),
    )
    assert existing.status_code == 200, existing.text

    verifier = secrets.token_urlsafe(32)
    response = await test_client.post(
        "/api/oauth2/install/requests",
        json=_payload("install-client-conflict", verifier),
    )
    assert response.status_code == 409
    assert response.json()["detail"]["error"] == "client_id_conflict"


@pytest.mark.asyncio
async def test_create_request_enforces_pending_quota(
    test_client: AsyncClient, monkeypatch
):
    """单 IP pending 上限 → 429"""
    from opentask.config import config

    monkeypatch.setattr(type(config), "oauth_install_max_pending_per_ip", property(lambda self: 1))

    # 用独立 X-Forwarded-For 隔离本用例的配额口径（避免与其他用例残留的 pending 互相影响）
    headers = {"X-Forwarded-For": "10.99.99.99"}
    verifier = secrets.token_urlsafe(32)
    response = await test_client.post(
        "/api/oauth2/install/requests", json=_payload("install-quota-1", verifier), headers=headers
    )
    assert response.status_code in (200, 201), response.text
    verifier2 = secrets.token_urlsafe(32)
    response = await test_client.post(
        "/api/oauth2/install/requests", json=_payload("install-quota-2", verifier2), headers=headers
    )
    assert response.status_code == 429
    assert response.json()["detail"]["error"] == "too_many_pending_requests"


@pytest.mark.asyncio
async def test_create_request_rate_limited_per_ip(test_client: AsyncClient, monkeypatch):
    """单 IP 每分钟创建速率超限 → 429 rate_limited"""
    from opentask.config import config

    monkeypatch.setattr(
        type(config), "oauth_install_rate_limit_per_minute", property(lambda self: 1)
    )
    headers = {"X-Forwarded-For": "10.77.77.77"}
    verifier = secrets.token_urlsafe(32)
    first = await test_client.post(
        "/api/oauth2/install/requests", json=_payload("install-rate-1", verifier), headers=headers
    )
    assert first.status_code in (200, 201), first.text

    verifier2 = secrets.token_urlsafe(32)
    second = await test_client.post(
        "/api/oauth2/install/requests", json=_payload("install-rate-2", verifier2), headers=headers
    )
    assert second.status_code == 429
    assert second.json()["detail"]["error"] == "rate_limited"


# ===== 批准 =====


@pytest.mark.asyncio
async def test_approve_requires_admin(test_client: AsyncClient, oauth_user: UserModel):
    """非管理员批准 → 403"""
    verifier = secrets.token_urlsafe(32)
    data = await _create_request(test_client, "install-client-approve-perm", verifier)

    response = await test_client.post(
        f"/api/oauth2/install/requests/{data['install_id']}/approve",
        headers=_viewer_bearer(oauth_user),
        json={"approved": True},
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_approve_returns_redirect_with_code_and_state(
    test_client: AsyncClient, admin_user: UserModel
):
    """批准 → redirect_to 带 code & state；且此时**尚未创建 client**"""
    verifier = secrets.token_urlsafe(32)
    data = await _create_request(test_client, "install-client-approve", verifier)
    approved = await _approve(test_client, data["install_id"], admin_user)

    assert approved["status"] == "APPROVED"
    assert approved["redirect_to"].startswith(CALLBACK_URL)
    assert "code=ins_" in approved["redirect_to"]
    assert "state=state-abc-123" in approved["redirect_to"]

    # 批准阶段不创建 client（client 在兑换时才创建）
    listing = await test_client.get(
        "/api/oauth2/clients", headers=_admin_bearer(admin_user)
    )
    client_ids = {row["client_id"] for row in listing.json()["data"]}
    assert "install-client-approve" not in client_ids


@pytest.mark.asyncio
async def test_approve_is_not_repeatable(test_client: AsyncClient, admin_user: UserModel):
    """重复批准 → 409（幂等保护，不重复签发安装码）"""
    verifier = secrets.token_urlsafe(32)
    data = await _create_request(test_client, "install-client-approve-twice", verifier)
    await _approve(test_client, data["install_id"], admin_user)

    response = await test_client.post(
        f"/api/oauth2/install/requests/{data['install_id']}/approve",
        headers=_admin_bearer(admin_user),
        json={"approved": True},
    )
    assert response.status_code == 409
    assert response.json()["detail"]["error"] == "install_request_not_pending"


@pytest.mark.asyncio
async def test_reject_marks_request_rejected(test_client: AsyncClient, admin_user: UserModel):
    """拒绝 → status=REJECTED"""
    verifier = secrets.token_urlsafe(32)
    data = await _create_request(test_client, "install-client-reject", verifier)

    response = await test_client.post(
        f"/api/oauth2/install/requests/{data['install_id']}/reject",
        headers=_admin_bearer(admin_user),
        json={},
    )
    assert response.status_code == 200
    assert response.json()["data"]["status"] == "REJECTED"


# ===== 兑换 =====


def _code_from_redirect(redirect_to: str) -> str:
    from urllib.parse import parse_qs, urlsplit

    return parse_qs(urlsplit(redirect_to).query)["code"][0]


@pytest.mark.asyncio
async def test_exchange_returns_secret_once_and_stores_only_hash(
    test_client: AsyncClient, admin_user: UserModel, test_session: AsyncSession
):
    """兑换 → 返回明文密钥；库内只有哈希；列表不含明文"""
    verifier = secrets.token_urlsafe(32)
    data = await _create_request(test_client, "install-client-exchange", verifier)
    approved = await _approve(test_client, data["install_id"], admin_user)
    code = _code_from_redirect(approved["redirect_to"])

    response = await test_client.post(
        "/api/oauth2/install/exchange",
        json={
            "install_id": data["install_id"],
            "code": code,
            "verifier": verifier,
        },
    )
    assert response.status_code == 200, response.text
    body = response.json()["data"]
    assert body["client_secret"].startswith("ocs_")
    assert body["recovered"] is False
    # 内容与批准时精确一致
    assert body["redirect_uris"] == [REDIRECT_URI]
    assert body["scopes"] == sorted(READ_SCOPES)

    # 库内只存哈希
    client = (
        await test_session.execute(
            select(OAuthClient).where(OAuthClient.client_id == "install-client-exchange")
        )
    ).scalars().first()
    assert client is not None
    assert body["client_secret"] not in client.client_secret_hash
    assert client.client_secret_hash == hashlib.sha256(
        body["client_secret"].encode()
    ).hexdigest()

    # 列表不含明文
    listing = await test_client.get(
        "/api/oauth2/clients", headers=_admin_bearer(admin_user)
    )
    assert body["client_secret"] not in listing.text


@pytest.mark.asyncio
async def test_exchange_rejects_wrong_verifier(test_client: AsyncClient, admin_user: UserModel):
    """verifier 与 challenge 不匹配 → 400"""
    verifier = secrets.token_urlsafe(32)
    data = await _create_request(test_client, "install-client-badverifier", verifier)
    approved = await _approve(test_client, data["install_id"], admin_user)
    code = _code_from_redirect(approved["redirect_to"])

    response = await test_client.post(
        "/api/oauth2/install/exchange",
        json={
            "install_id": data["install_id"],
            "code": code,
            "verifier": secrets.token_urlsafe(32),
        },
    )
    assert response.status_code == 400
    assert response.json()["detail"]["error"] == "invalid_verifier"


@pytest.mark.asyncio
async def test_exchange_rejects_wrong_code(test_client: AsyncClient, admin_user: UserModel):
    """安装码错误 → 400"""
    verifier = secrets.token_urlsafe(32)
    data = await _create_request(test_client, "install-client-badcode", verifier)
    await _approve(test_client, data["install_id"], admin_user)

    response = await test_client.post(
        "/api/oauth2/install/exchange",
        json={
            "install_id": data["install_id"],
            "code": "ins_" + "0" * 32,
            "verifier": verifier,
        },
    )
    assert response.status_code == 400
    assert response.json()["detail"]["error"] == "invalid_install_code"


@pytest.mark.asyncio
async def test_exchange_rejects_not_approved(test_client: AsyncClient):
    """未批准即兑换 → 409"""
    verifier = secrets.token_urlsafe(32)
    data = await _create_request(test_client, "install-client-notapproved", verifier)

    response = await test_client.post(
        "/api/oauth2/install/exchange",
        json={
            "install_id": data["install_id"],
            "code": "ins_" + "1" * 32,
            "verifier": verifier,
        },
    )
    assert response.status_code == 409
    assert response.json()["detail"]["error"] == "install_not_approved"


@pytest.mark.asyncio
async def test_exchange_code_expired(test_client: AsyncClient, admin_user: UserModel, monkeypatch):
    """安装码过期 → 400 install_code_expired"""
    from opentask.config import config

    monkeypatch.setattr(type(config), "oauth_install_code_ttl_seconds", property(lambda self: -1))

    verifier = secrets.token_urlsafe(32)
    data = await _create_request(test_client, "install-client-codeexpired", verifier)
    approved = await _approve(test_client, data["install_id"], admin_user)
    code = _code_from_redirect(approved["redirect_to"])

    response = await test_client.post(
        "/api/oauth2/install/exchange",
        json={"install_id": data["install_id"], "code": code, "verifier": verifier},
    )
    assert response.status_code == 400
    assert response.json()["detail"]["error"] == "install_code_expired"


@pytest.mark.asyncio
async def test_recovery_window_returns_new_secret(
    test_client: AsyncClient, admin_user: UserModel
):
    """已消费 → 恢复窗口内用同一 verifier 重试 → 200 且换发**新密钥**"""
    verifier = secrets.token_urlsafe(32)
    data = await _create_request(test_client, "install-client-recover", verifier)
    approved = await _approve(test_client, data["install_id"], admin_user)
    code = _code_from_redirect(approved["redirect_to"])

    first = await test_client.post(
        "/api/oauth2/install/exchange",
        json={"install_id": data["install_id"], "code": code, "verifier": verifier},
    )
    assert first.status_code == 200
    first_secret = first.json()["data"]["client_secret"]

    # 响应丢失后的重试：同 verifier → 恢复路径
    second = await test_client.post(
        "/api/oauth2/install/exchange",
        json={"install_id": data["install_id"], "code": code, "verifier": verifier},
    )
    assert second.status_code == 200, second.text
    body = second.json()["data"]
    assert body["recovered"] is True
    assert body["client_secret"] != first_secret
    assert body["client_secret"].startswith("ocs_")


@pytest.mark.asyncio
async def test_consumed_outside_recovery_window_is_explicit_failure(
    test_client: AsyncClient, admin_user: UserModel, monkeypatch
):
    """已消费且恢复窗口已过 → 409（**明确失败**，不得假报成功）"""
    from opentask.config import config

    monkeypatch.setattr(type(config), "oauth_install_recovery_window_seconds", property(lambda self: -1))

    verifier = secrets.token_urlsafe(32)
    data = await _create_request(test_client, "install-client-norecover", verifier)
    approved = await _approve(test_client, data["install_id"], admin_user)
    code = _code_from_redirect(approved["redirect_to"])

    first = await test_client.post(
        "/api/oauth2/install/exchange",
        json={"install_id": data["install_id"], "code": code, "verifier": verifier},
    )
    assert first.status_code == 200

    second = await test_client.post(
        "/api/oauth2/install/exchange",
        json={"install_id": data["install_id"], "code": code, "verifier": verifier},
    )
    assert second.status_code == 409
    detail = second.json()["detail"]
    assert detail["error"] == "install_already_consumed"
    # 失败响应不得含 client_secret
    assert "client_secret" not in json.dumps(second.json())


# ===== 状态查询 =====


@pytest.mark.asyncio
async def test_status_requires_matching_verifier(test_client: AsyncClient):
    """verifier 不匹配 → 404（不泄露申请是否存在）"""
    verifier = secrets.token_urlsafe(32)
    data = await _create_request(test_client, "install-client-status", verifier)

    response = await test_client.post(
        "/api/oauth2/install/status",
        json={
            "install_id": data["install_id"],
            "verifier": secrets.token_urlsafe(32),
        },
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_status_reports_recoverable(test_client: AsyncClient, admin_user: UserModel):
    """状态查询：不含密钥；已消费且在窗口内 → recoverable=true"""
    verifier = secrets.token_urlsafe(32)
    data = await _create_request(test_client, "install-client-status2", verifier)
    approved = await _approve(test_client, data["install_id"], admin_user)
    code = _code_from_redirect(approved["redirect_to"])

    await test_client.post(
        "/api/oauth2/install/exchange",
        json={"install_id": data["install_id"], "code": code, "verifier": verifier},
    )

    response = await test_client.post(
        "/api/oauth2/install/status",
        json={"install_id": data["install_id"], "verifier": verifier},
    )
    assert response.status_code == 200
    body = response.json()["data"]
    assert body["status"] == "CONSUMED"
    assert body["recoverable"] is True
    assert "client_secret" not in response.text


# ===== 审计列表 =====


@pytest.mark.asyncio
async def test_admin_list_requires_admin(test_client: AsyncClient, oauth_user: UserModel):
    """审计列表 → 非管理员 403"""
    response = await test_client.get(
        "/api/oauth2/install/requests", headers=_viewer_bearer(oauth_user)
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_admin_list_hides_sensitive_fields(test_client: AsyncClient, admin_user: UserModel):
    """审计列表不含安装码 / challenge / state"""
    verifier = secrets.token_urlsafe(32)
    data = await _create_request(test_client, "install-client-audit", verifier)
    await _approve(test_client, data["install_id"], admin_user)

    response = await test_client.get(
        "/api/oauth2/install/requests", headers=_admin_bearer(admin_user)
    )
    assert response.status_code == 200
    text = response.text
    assert "code_hash" not in text
    assert "code_challenge" not in text
    assert "state-abc-123" not in text
    assert "ins_" not in text


# ===== 日志不泄密 =====


@pytest.mark.asyncio
async def test_logs_do_not_leak_code_or_secret(
    test_client: AsyncClient, admin_user: UserModel, caplog
):
    """安装码 / verifier / client_secret 不进日志"""
    import logging

    caplog.set_level(logging.INFO)
    verifier = secrets.token_urlsafe(32)
    data = await _create_request(test_client, "install-client-logs", verifier)
    approved = await _approve(test_client, data["install_id"], admin_user)
    code = _code_from_redirect(approved["redirect_to"])

    response = await test_client.post(
        "/api/oauth2/install/exchange",
        json={"install_id": data["install_id"], "code": code, "verifier": verifier},
    )
    assert response.status_code == 200
    secret = response.json()["data"]["client_secret"]

    logged = "\n".join(record.getMessage() for record in caplog.records)
    assert code not in logged
    assert secret not in logged
    assert verifier not in logged
