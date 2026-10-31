"""契约层鉴权 + 能力声明用例（S5 验收 S2/S3）

- 401 独立语义：缺/错凭证一律 401，错误体带可辨识错误码字段
  （detail.code ∈ CONTRACT_AUTH_MISSING / CONTRACT_AUTH_INVALID），
  区别于 403/503；合法凭证 200
- 两模式贯通：Bearer API Key（vk_，access_tokens 表校验）与
  OAuth2 client credentials（POST /tasks/token 换 JWT 后访问）
- GET /capabilities 公开返回端点支持情况 + 契约版本 + 鉴权模式 + 生效词表
"""

import uuid

import pytest

from .conftest import TITLE_PREFIX, create_api_key
from opentask.api.tasks.schemas import CONTRACT_VERSION


def _err_code(resp) -> str:
    """取 401/400 错误体中的错误码字段（可辨识错误码契约）"""
    return resp.json()["detail"]["code"]


# ============================================================================
# S2: 401 独立语义（raw_client → 真实 authenticate_contract）
# ============================================================================


@pytest.mark.asyncio
class TestContractAuth401:
    async def test_missing_credentials_401_with_code(self, raw_client):
        """无 Authorization 头：401 + CONTRACT_AUTH_MISSING + WWW-Authenticate"""
        resp = await raw_client.get("/tasks")
        assert resp.status_code == 401  # 非 403：契约层缺凭证语义独立
        assert _err_code(resp) == "CONTRACT_AUTH_MISSING"
        assert "Bearer" in resp.headers["WWW-Authenticate"]

    async def test_non_bearer_scheme_401(self, raw_client):
        resp = await raw_client.get(
            "/tasks", headers={"Authorization": "Basic dXNlcjpwYXNz"}
        )
        assert resp.status_code == 401
        assert _err_code(resp) == "CONTRACT_AUTH_MISSING"

    async def test_bogus_api_key_401(self, raw_client):
        """错误 API Key：401 + CONTRACT_AUTH_INVALID"""
        resp = await raw_client.get(
            "/tasks", headers={"Authorization": "Bearer vk_bogus"}
        )
        assert resp.status_code == 401
        assert _err_code(resp) == "CONTRACT_AUTH_INVALID"

    async def test_garbage_jwt_401(self, raw_client):
        """非 vk_ 的乱串按 JWT 校验失败：401 + CONTRACT_AUTH_INVALID"""
        resp = await raw_client.get(
            "/tasks", headers={"Authorization": "Bearer not-a-jwt"}
        )
        assert resp.status_code == 401
        assert _err_code(resp) == "CONTRACT_AUTH_INVALID"

    async def test_expired_api_key_401(self, raw_client, db, test_user):
        """过期 API Key：validate_token 返回 None → 401"""
        expired = await create_api_key(db, test_user, name="ct-expired",
                                       expires_days=-1)
        resp = await raw_client.get(
            "/tasks", headers={"Authorization": f"Bearer {expired}"}
        )
        assert resp.status_code == 401
        assert _err_code(resp) == "CONTRACT_AUTH_INVALID"

    async def test_disabled_user_api_key_401(self, raw_client, db, test_user):
        """禁用用户的 API Key：用户状态拦截 → 401"""
        key = await create_api_key(db, test_user, name="ct-disabled")
        test_user.status = 0
        await db.commit()

        resp = await raw_client.get(
            "/tasks", headers={"Authorization": f"Bearer {key}"}
        )
        assert resp.status_code == 401
        assert _err_code(resp) == "CONTRACT_AUTH_INVALID"

    async def test_valid_api_key_200(self, raw_client, db, test_user, assignee_user):
        """合法 API Key：GET 列表 200（S2「合法凭证正常」）"""
        key = await create_api_key(db, test_user, name="ct-valid")
        resp = await raw_client.get(
            "/tasks",
            params={"assignee": str(assignee_user.id)},
            headers={"Authorization": f"Bearer {key}"},
        )
        assert resp.status_code == 200, resp.text
        assert "items" in resp.json()

    async def test_all_task_endpoints_enforce_auth(self, raw_client):
        """五个 /tasks 端点全部要求凭证（读端点同样受保护）"""
        task_id = str(uuid.uuid4())
        cases = [
            ("get", "/tasks", {}),
            ("post", "/tasks", {"json": {"title": f"{TITLE_PREFIX}鉴权"}}),
            ("get", f"/tasks/{task_id}", {}),
            ("patch", f"/tasks/{task_id}", {"json": {"title": "x"}}),
            ("delete", f"/tasks/{task_id}", {}),
        ]
        for method, path, kwargs in cases:
            resp = await getattr(raw_client, method)(path, **kwargs)
            assert resp.status_code == 401, (method, path, resp.status_code)
            assert _err_code(resp) == "CONTRACT_AUTH_MISSING"


# ============================================================================
# S2: OAuth2 client credentials（token 交换端点）
# ============================================================================


@pytest.mark.asyncio
class TestClientCredentialsToken:
    async def _get_key(self, db, test_user) -> str:
        return await create_api_key(db, test_user, name="ct-oauth")

    async def test_exchange_and_use_jwt(self, raw_client, db, test_user):
        """client_secret=API Key 换 JWT；返回 OAuth2 形状；JWT 访问 /tasks 200"""
        key = await self._get_key(db, test_user)

        resp = await raw_client.post(
            "/tasks/token",
            data={
                "grant_type": "client_credentials",
                "client_secret": key,
            },
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["token_type"] == "Bearer"
        assert body["access_token"]
        assert isinstance(body["expires_in"], int) and body["expires_in"] > 0
        assert "refresh_token" not in body  # RFC 6749 §4.4.3

        # 换到的 JWT 走契约鉴权 → 200
        resp = await raw_client.get(
            "/tasks", headers={"Authorization": f"Bearer {body['access_token']}"}
        )
        assert resp.status_code == 200, resp.text

    async def test_exchange_with_matching_client_id_200(
        self, raw_client, db, test_user
    ):
        """client_id 与 Key 归属用户一致：200（双重校验通过）"""
        key = await self._get_key(db, test_user)
        resp = await raw_client.post(
            "/tasks/token",
            data={
                "grant_type": "client_credentials",
                "client_id": str(test_user.id),
                "client_secret": key,
            },
        )
        assert resp.status_code == 200, resp.text

    async def test_exchange_client_id_mismatch_401(self, raw_client, db, test_user):
        """client_id 与 Key 归属用户不一致：401 INVALID"""
        key = await self._get_key(db, test_user)
        resp = await raw_client.post(
            "/tasks/token",
            data={
                "grant_type": "client_credentials",
                "client_id": str(uuid.uuid4()),
                "client_secret": key,
            },
        )
        assert resp.status_code == 401
        assert _err_code(resp) == "CONTRACT_AUTH_INVALID"

    async def test_exchange_wrong_secret_401(self, raw_client):
        resp = await raw_client.post(
            "/tasks/token",
            data={
                "grant_type": "client_credentials",
                "client_secret": "vk_wrong-secret",
            },
        )
        assert resp.status_code == 401
        assert _err_code(resp) == "CONTRACT_AUTH_INVALID"

    async def test_exchange_missing_secret_401(self, raw_client):
        resp = await raw_client.post(
            "/tasks/token", data={"grant_type": "client_credentials"}
        )
        assert resp.status_code == 401
        assert _err_code(resp) == "CONTRACT_AUTH_MISSING"

    async def test_exchange_unsupported_grant_type_400(self, raw_client, db, test_user):
        """非 client_credentials 的 grant：400（语义区别于凭证错误 401）"""
        key = await self._get_key(db, test_user)
        resp = await raw_client.post(
            "/tasks/token",
            data={"grant_type": "password", "client_secret": key},
        )
        assert resp.status_code == 400
        assert _err_code(resp) == "CONTRACT_AUTH_UNSUPPORTED_GRANT"


# ============================================================================
# S3: capabilities 能力声明（公开端点）
# ============================================================================


@pytest.mark.asyncio
class TestCapabilities:
    async def test_capabilities_public_and_shape(self, raw_client):
        """无凭证可访问；返回契约版本、端点支持、鉴权模式、状态词表"""
        resp = await raw_client.get("/capabilities")
        assert resp.status_code == 200, resp.text
        body = resp.json()

        assert body["contract_version"] == CONTRACT_VERSION
        assert body["endpoints"] == {
            "list_tasks": "GET /tasks",
            "create_task": "POST /tasks",
            "get_task": "GET /tasks/{task_id}",
            "update_task": "PATCH /tasks/{task_id}",
            "delete_task": "DELETE /tasks/{task_id}",
            "issue_token": "POST /tasks/token",
            "capabilities": "GET /capabilities",
        }
        assert body["features"]["incremental_cursor"] == "updated_since"
        assert body["features"]["delete_semantics"] == "soft"
        assert body["features"]["pagination"] == "limit_offset"

        auth = body["auth"]
        assert set(auth["modes"]) == {"bearer_api_key", "oauth2_client_credentials"}
        assert auth["token_endpoint"] == "/tasks/token"
        assert auth["api_key_prefix"] == "vk_"

        # 生效词表（默认配置 = 5 通用状态）
        assert body["status_vocabulary"] == sorted(
            {"todo", "in_progress", "in_review", "done", "cancelled"}
        )
        assert body["features"]["status_mapping_source"] in ("config", "default")

    async def test_capabilities_reflects_mapping_config(
        self, raw_client, mapping_config
    ):
        """词表与映射来源随 contract 配置变化（配置化能力自描述）"""
        mapping_config(
            {"contract": {"status_mapping": {
                "open": "todo",
                "in_progress": "in_progress",
                "feedback": "todo",
                "resolved": "done",
                "closed": "done",
                "rejected": "cancelled",
            }}}
        )
        body = (await raw_client.get("/capabilities")).json()
        assert body["features"]["status_mapping_source"] == "config"
        assert body["status_vocabulary"] == sorted(
            {"todo", "in_progress", "done", "cancelled"}
        )

        mapping_config(None)
        body = (await raw_client.get("/capabilities")).json()
        assert body["features"]["status_mapping_source"] == "default"
        assert "in_review" in body["status_vocabulary"]
