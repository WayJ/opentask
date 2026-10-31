"""
本地登录与 token 自动刷新测试

测试范围：
- login() 明文密码提交 + token/refresh_token 保存
- 401 → refresh_token 刷新 → 重试原请求
- refresh 失效 → 凭据重登 → 重试成功
- refresh + 重登均失败 → 清空 keyring/config 凭据 + 明确错误信息
- clear_auth 清空 token/access_token/refresh_token
"""

from unittest import mock

import pytest

from opentask.utils import password_store
from opentask.utils.password_store import PasswordStore
from opentask.utils.api_client import OpenTaskClient, APIError
from opentask.utils.crypto_helper import encrypt_password

BASE_URL = "http://test-api.example.com"


# ============================================================================
# 测试辅助：模拟 httpx.AsyncClient
# ============================================================================

def make_response(status_code: int = 200, json_data: dict | None = None):
    """构造 mock httpx.Response"""
    response = mock.Mock()
    response.status_code = status_code
    response.json.return_value = json_data if json_data is not None else {}
    return response


class FakeAsyncClient:
    """模拟 httpx.AsyncClient，把所有请求转发给 handler

    handler(method, url, json_body) -> mock response
    """

    def __init__(self, handler):
        self.handler = handler

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc_info):
        return False

    async def request(self, method, url, headers=None, **kwargs):
        return self.handler(method, url, kwargs.get("json"))

    async def post(self, url, json=None, headers=None, **kwargs):
        return self.handler("POST", url, json)

    async def get(self, url, headers=None, **kwargs):
        return self.handler("GET", url, kwargs.get("json"))


class RequestRouter:
    """按 URL 路径分发的请求脚本（每个路径一个 FIFO 响应队列）"""

    def __init__(self):
        self.requests = []  # 记录 (method, path, json)
        self._routes = {}

    def on(self, path, *responses):
        """为路径注册依次返回的响应"""
        self._routes[path] = list(responses)

    def handler(self, method, url, json_body=None):
        path = url.replace(BASE_URL, "")
        self.requests.append((method, path, json_body))
        for route_path, responses in self._routes.items():
            if path.startswith(route_path):
                assert responses, f"No more scripted responses for {method} {path}"
                return responses.pop(0)
        raise AssertionError(f"Unexpected request: {method} {path}")


@pytest.fixture
def http_router():
    """捕获请求并按脚本返回响应"""
    router = RequestRouter()
    with mock.patch(
        "opentask.utils.api_client.httpx.AsyncClient",
        lambda *args, **kwargs: FakeAsyncClient(router.handler)
    ):
        yield router


@pytest.fixture
def fake_keyring(monkeypatch):
    """用内存 dict 替代系统 keyring，避免测试污染真实凭据存储"""
    store = {}
    monkeypatch.setattr(password_store, "KEYRING_AVAILABLE", True)
    monkeypatch.setattr(
        PasswordStore, "set_password",
        staticmethod(lambda u, p: (store.__setitem__(u, p), True)[1])
    )
    monkeypatch.setattr(
        PasswordStore, "get_password",
        staticmethod(lambda u: store.get(u))
    )
    monkeypatch.setattr(
        PasswordStore, "delete_password",
        staticmethod(lambda u: (store.pop(u, None), True)[1])
    )
    return store


def ok(data: dict):
    """标准成功响应 {"code": 200, "data": ...}"""
    return make_response(200, {"code": 200, "data": data})


def unauthorized(message: str = "token expired"):
    """401 响应"""
    return make_response(401, {"code": 401, "message": message})


# ============================================================================
# 登录测试
# ============================================================================

class TestLoginPlaintext:
    """测试 login() 明文密码提交与 token 保存"""

    @pytest.mark.asyncio
    async def test_login_sends_plaintext_password_and_saves_tokens(
        self, clean_config, fake_keyring, http_router
    ):
        """登录成功：请求体密码是明文，config 保存 token + refresh_token"""
        http_router.on(
            "/api/auth/login",
            ok({"token": "tok-1", "refreshToken": "ref-1"})
        )

        client = OpenTaskClient(base_url=BASE_URL, config=clean_config)
        result = await client.login("alice", "plain-secret")

        assert result["token"] == "tok-1"
        assert clean_config.token == "tok-1"
        assert clean_config.refresh_token == "ref-1"
        # 凭据已保存（keyring 优先）
        assert clean_config.username == "alice"
        assert clean_config.password == "plain-secret"

        # 请求体密码是明文（不等于 encrypt_password 结果）
        method, path, body = http_router.requests[0]
        assert method == "POST"
        assert path == "/api/auth/login"
        assert body == {"userName": "alice", "password": "plain-secret"}
        assert body["password"] != encrypt_password("plain-secret")


# ============================================================================
# 401 自动刷新测试
# ============================================================================

class TestAutoRefresh:
    """测试业务请求 401 后自动走 refresh-token"""

    @pytest.mark.asyncio
    async def test_401_triggers_refresh_and_retry(self, clean_config, http_router):
        """401 → refresh-token 成功 → 重试成功，两个 token 均更新"""
        clean_config.token = "tok-old"
        clean_config.refresh_token = "ref-old"

        http_router.on(
            "/api/projects",
            unauthorized(),
            ok({"rows": [{"id": "p1"}], "total": 1})
        )
        http_router.on(
            "/api/auth/refresh-token",
            ok({"token": "tok-new", "refreshToken": "ref-new"})
        )

        client = OpenTaskClient(base_url=BASE_URL, config=clean_config)
        result = await client.get("/api/projects")

        assert result["total"] == 1
        assert clean_config.token == "tok-new"
        assert clean_config.refresh_token == "ref-new"

        # 请求顺序: 业务请求 → refresh → 业务重试
        sequence = [(m, p) for m, p, _ in http_router.requests]
        assert sequence == [
            ("GET", "/api/projects"),
            ("POST", "/api/auth/refresh-token"),
            ("GET", "/api/projects"),
        ]
        # refresh 请求体带 refreshToken
        refresh_body = http_router.requests[1][2]
        assert refresh_body == {"refreshToken": "ref-old"}
        # 重试时使用新 token
        # (headers 不在 router 中记录，通过 config 状态断言已覆盖)

    @pytest.mark.asyncio
    async def test_refresh_without_saved_refresh_token_fails(
        self, clean_config, http_router
    ):
        """无 refresh_token 时 refresh() 直接返回 False"""
        clean_config._data = {}
        client = OpenTaskClient(base_url=BASE_URL, config=clean_config)
        assert await client.refresh() is False
        assert http_router.requests == []


# ============================================================================
# refresh 失效走重登测试
# ============================================================================

class TestReloginFallback:
    """测试 refresh 401 后使用保存的凭据重登"""

    @pytest.mark.asyncio
    async def test_refresh_401_falls_back_to_relogin(
        self, clean_config, fake_keyring, http_router
    ):
        """refresh 401 → 凭据重登成功 → 重试成功"""
        clean_config.username = "alice"
        clean_config.password = "plain-secret"  # 存入 fake keyring
        clean_config.token = "tok-old"
        clean_config.refresh_token = "ref-old"

        http_router.on(
            "/api/projects",
            unauthorized(),
            ok({"rows": [], "total": 0})
        )
        http_router.on(
            "/api/auth/refresh-token",
            unauthorized("refresh token expired")
        )
        http_router.on(
            "/api/auth/login",
            ok({"token": "tok-relogin", "refreshToken": "ref-relogin"})
        )

        client = OpenTaskClient(base_url=BASE_URL, config=clean_config)
        result = await client.get("/api/projects")

        assert result["total"] == 0
        assert clean_config.token == "tok-relogin"
        assert clean_config.refresh_token == "ref-relogin"

        # 请求顺序: 业务请求 → refresh(401) → login → 业务重试
        sequence = [(m, p) for m, p, _ in http_router.requests]
        assert sequence == [
            ("GET", "/api/projects"),
            ("POST", "/api/auth/refresh-token"),
            ("POST", "/api/auth/login"),
            ("GET", "/api/projects"),
        ]
        # 重登请求体使用明文密码
        login_body = http_router.requests[2][2]
        assert login_body == {"userName": "alice", "password": "plain-secret"}
        # 重登成功后凭据未被清空
        assert clean_config.username == "alice"
        assert "alice" in fake_keyring


# ============================================================================
# 凭据过期清空测试
# ============================================================================

class TestCredentialsExpired:
    """测试 refresh + 重登均失败时清空凭据并报明确错误"""

    @pytest.mark.asyncio
    async def test_refresh_and_relogin_both_fail_clears_credentials(
        self, clean_config, fake_keyring, http_router
    ):
        """refresh 401 + 重登 401 → 凭据被清空 + 返回明确错误"""
        clean_config.username = "alice"
        clean_config.password = "plain-secret"
        clean_config.token = "tok-old"
        clean_config.refresh_token = "ref-old"

        http_router.on("/api/projects", unauthorized())
        http_router.on("/api/auth/refresh-token", unauthorized("refresh token expired"))
        http_router.on("/api/auth/login", unauthorized("用户名或密码错误"))

        client = OpenTaskClient(base_url=BASE_URL, config=clean_config)
        with pytest.raises(APIError) as exc_info:
            await client.get("/api/projects")

        # 错误信息明确提示重新登录
        assert "凭据已过期" in exc_info.value.message
        assert "opentask login" in exc_info.value.message

        # 凭据被清空（config + keyring）
        assert clean_config.username is None
        assert clean_config.get("a_p") is None
        assert clean_config.get("a_u") is None
        assert clean_config.refresh_token is None
        assert "alice" not in fake_keyring

        # 不无限重试: 业务请求只发一次，login 只尝试一次
        login_calls = [r for r in http_router.requests if r[1] == "/api/auth/login"]
        assert len(login_calls) == 1
        assert len(http_router.requests) == 3  # 业务 + refresh + login


# ============================================================================
# clear_auth 测试
# ============================================================================

class TestClearAuth:
    """测试 clear_auth 清空三个键"""

    def test_clear_auth_removes_all_auth_keys(self, clean_config):
        """clear_auth 清空 token / access_token / refresh_token"""
        clean_config.token = "tok"
        clean_config.access_token = "vk_abc"
        clean_config.refresh_token = "ref"

        clean_config.clear_auth()

        assert clean_config.token is None
        assert clean_config.access_token is None
        assert clean_config.refresh_token is None
        assert clean_config.get("token") is None
        assert clean_config.get("access_token") is None
        assert clean_config.get("refresh_token") is None
