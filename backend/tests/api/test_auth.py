"""
认证系统测试

测试范围：
- JNPF OAuth 登录 (/api/auth/login)
- 本地登录 (/api/auth/login-local)
- 获取用户信息 (/api/auth/getUserInfo)
- 登出 (/api/auth/logout)
"""

import pytest
from unittest import mock
from httpx import AsyncClient
from passlib.context import CryptContext

# 密码哈希上下文（bcrypt），与 opentask.auth 保持一致
_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# ============================================================================
# 本地登录测试
# ============================================================================

@pytest.mark.asyncio
async def test_login_local_success(test_client: AsyncClient, test_session):
    """测试本地登录成功"""
    # 首先创建测试用户
    from opentask.models.user.model import UserModel

    test_user = UserModel(
        name="testuser",
        password_hash=_pwd_context.hash("password123"),  # bcrypt 哈希
        jnpf_user_id="test_jnpf_id",
        jnpf_name="Test User"
    )
    test_session.add(test_user)
    await test_session.commit()

    # 测试登录
    response = await test_client.post(
        "/api/auth/login-local",
        json={
            "userName": "testuser",
            "password": "password123"
        }
    )

    assert response.status_code == 200
    data = response.json()
    assert data["code"] == 200
    assert "token" in data["data"]
    assert data["data"]["username"] == "testuser"
    assert "userId" in data["data"]


@pytest.mark.asyncio
async def test_login_local_wrong_password(test_client: AsyncClient, test_session):
    """测试本地登录 - 错误密码"""
    from opentask.models.user.model import UserModel

    # 创建测试用户
    test_user = UserModel(
        name="testuser",
        password_hash=_pwd_context.hash("password123"),  # bcrypt 哈希
        jnpf_user_id="test_jnpf_id"
    )
    test_session.add(test_user)
    await test_session.commit()

    # 测试错误密码
    response = await test_client.post(
        "/api/auth/login-local",
        json={
            "userName": "testuser",
            "password": "wrongpassword"
        }
    )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_login_local_user_not_found(test_client: AsyncClient):
    """测试本地登录 - 用户不存在"""
    response = await test_client.post(
        "/api/auth/login-local",
        json={
            "userName": "nonexistent",
            "password": "password"
        }
    )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_login_local_missing_fields(test_client: AsyncClient):
    """测试本地登录 - 缺少必填字段"""
    response = await test_client.post(
        "/api/auth/login-local",
        json={
            "userName": "testuser"
            # 缺少 password
        }
    )

    assert response.status_code == 422  # Validation error


# ============================================================================
# JNPF OAuth 登录测试 (使用 Mock)
# ============================================================================

@pytest.mark.asyncio
@mock.patch("opentask.api.auth.router.httpx.AsyncClient")
async def test_login_jnpf_success(mock_httpx, monkeypatch, test_client: AsyncClient, test_session):
    """测试 JNPF OAuth 登录成功（需显式启用 JNPF，/login 默认走本地路径）"""
    monkeypatch.setenv("AUTH_JNPF_ENABLED", "true")
    # Mock JNPF 登录响应
    mock_login_response = mock.Mock()
    mock_login_response.status_code = 200
    mock_login_response.json.return_value = {
        "code": 200,
        "data": {
            "token": "bearer test_jnpf_token_12345"
        }
    }

    # Mock JNPF 用户信息响应
    mock_user_response = mock.Mock()
    mock_user_response.status_code = 200
    mock_user_response.json.return_value = {
        "code": 200,
        "data": {
            "userInfo": {
                "userId": "jnpf_user_123",
                "userName": "JNPF User",
                "userAccount": "jnpf_account",
                "organizeId": "org_123",
                "organizeName": "Test Org"
            }
        }
    }

    # 设置 AsyncClient context manager 的行为
    mock_client_instance = mock.AsyncMock()
    mock_client_instance.__aenter__.return_value = mock_client_instance
    mock_client_instance.__aexit__.return_value = mock.AsyncMock(return_value=None)

    # 链式调用 mock
    mock_client_instance.post = mock.AsyncMock(return_value=mock_login_response)
    mock_client_instance.get = mock.AsyncMock(return_value=mock_user_response)

    mock_httpx.return_value = mock_client_instance

    # 测试登录
    response = await test_client.post(
        "/api/auth/login",
        json={
            "userName": "jnpf_user",
            "password": "encrypted_password"
        }
    )

    assert response.status_code == 200
    data = response.json()
    assert data["code"] == 200
    assert "token" in data["data"]
    assert data["data"]["refreshToken"]  # JNPF 路径同样签发 refresh token
    assert data["data"]["username"] == "JNPF User"


@pytest.mark.asyncio
@mock.patch("opentask.api.auth.router.httpx.AsyncClient")
async def test_login_jnpf_invalid_credentials(mock_httpx, monkeypatch, test_client: AsyncClient):
    """测试 JNPF OAuth 登录 - 无效凭据（需显式启用 JNPF）"""
    monkeypatch.setenv("AUTH_JNPF_ENABLED", "true")
    # Mock JNPF 登录失败响应
    mock_login_response = mock.Mock()
    mock_login_response.status_code = 200
    mock_login_response.json.return_value = {
        "code": 401,
        "msg": "用户名或密码错误"
    }

    mock_client_instance = mock.AsyncMock()
    mock_client_instance.__aenter__.return_value = mock_client_instance
    mock_client_instance.__aexit__.return_value = mock.AsyncMock(return_value=None)
    mock_client_instance.post = mock.AsyncMock(return_value=mock_login_response)

    mock_httpx.return_value = mock_client_instance

    # 测试登录
    response = await test_client.post(
        "/api/auth/login",
        json={
            "userName": "wrong_user",
            "password": "wrong_password"
        }
    )

    assert response.status_code == 401


@pytest.mark.asyncio
@mock.patch("opentask.api.auth.router.httpx.AsyncClient")
async def test_login_jnpf_timeout(mock_httpx, monkeypatch, test_client: AsyncClient):
    """测试 JNPF OAuth 登录 - 超时（需显式启用 JNPF）"""
    import httpx

    monkeypatch.setenv("AUTH_JNPF_ENABLED", "true")

    # Mock 超时异常
    mock_client_instance = mock.AsyncMock()
    mock_client_instance.__aenter__.side_effect = httpx.TimeoutException("Request timeout")
    mock_client_instance.__aexit__.return_value = mock.AsyncMock(return_value=None)

    mock_httpx.return_value = mock_client_instance

    # 测试登录超时
    response = await test_client.post(
        "/api/auth/login",
        json={
            "userName": "testuser",
            "password": "password"
        }
    )

    assert response.status_code == 504  # Gateway Timeout


# ============================================================================
# 获取用户信息测试
# ============================================================================

@pytest.mark.asyncio
async def test_get_user_info_success(test_client: AsyncClient, test_token):
    """测试获取用户信息成功"""
    response = await test_client.get(
        "/api/auth/getUserInfo",
        headers={"Authorization": f"Bearer {test_token}"}
    )

    assert response.status_code == 200
    data = response.json()
    assert data["code"] == 200
    assert "userId" in data["data"]
    assert "userName" in data["data"]
    assert "roles" in data["data"]


@pytest.mark.asyncio
async def test_get_user_info_no_token(test_client: AsyncClient):
    """测试获取用户信息 - 缺少 token"""
    response = await test_client.get("/api/auth/getUserInfo")

    assert response.status_code == 401  # Unauthorized


@pytest.mark.asyncio
async def test_get_user_info_invalid_token(test_client: AsyncClient):
    """测试获取用户信息 - 无效 token"""
    response = await test_client.get(
        "/api/auth/getUserInfo",
        headers={"Authorization": "Bearer invalid_token"}
    )

    assert response.status_code == 401  # Unauthorized


# ============================================================================
# 登出测试
# ============================================================================

@pytest.mark.asyncio
async def test_logout_success(test_client: AsyncClient):
    """测试登出成功"""
    response = await test_client.post("/api/auth/logout")

    assert response.status_code == 200
    data = response.json()
    assert data["code"] == 200
    assert "Successfully logged out" in data["message"]


# ============================================================================
# HEAD 请求测试
# ============================================================================

@pytest.mark.asyncio
async def test_login_head(test_client: AsyncClient):
    """测试登录端点的 HEAD 请求"""
    response = await test_client.head("/api/auth/login")

    assert response.status_code == 200


# ============================================================================
# 禁用用户 token 失效测试
# ============================================================================

@pytest.mark.asyncio
async def test_disabled_user_token_rejected(test_client: AsyncClient, test_session):
    """被禁用用户（status=0）持有效 JWT 也必须 401"""
    from opentask.models.user.model import UserModel
    from opentask.jwt_utils import create_access_token

    user = UserModel(name="disableduser", status=0)
    test_session.add(user)
    await test_session.commit()

    token = create_access_token({"sub": "disableduser"})
    resp = await test_client.get(
        "/api/auth/getUserInfo",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_enabled_user_token_accepted(test_client: AsyncClient, test_session):
    """正常用户（status=1）token 仍可用"""
    from opentask.models.user.model import UserModel
    from opentask.jwt_utils import create_access_token

    user = UserModel(name="activeuser", status=1)
    test_session.add(user)
    await test_session.commit()

    token = create_access_token({"sub": "activeuser"})
    resp = await test_client.get(
        "/api/auth/getUserInfo",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
