"""
认证中间件测试

测试范围：
- JWT Token 验证
- Token 过期检查
- 权限检查
- 错误处理
"""

import pytest
from unittest import mock
from httpx import AsyncClient


# ============================================================================
# JWT Token 验证测试
# ============================================================================

@pytest.mark.asyncio
async def test_valid_token(test_client: AsyncClient, test_token):
    """测试有效 Token"""
    response = await test_client.get(
        "/api/auth/getUserInfo",
        headers={"Authorization": f"Bearer {test_token}"}
    )

    assert response.status_code == 200


@pytest.mark.asyncio
async def test_missing_token(test_client: AsyncClient):
    """测试缺少 Token"""
    response = await test_client.get("/api/auth/getUserInfo")

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_invalid_token_format(test_client: AsyncClient):
    """测试无效 Token 格式"""
    response = await test_client.get(
        "/api/auth/getUserInfo",
        headers={"Authorization": "InvalidFormat token"}
    )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_invalid_token(test_client: AsyncClient):
    """测试无效 Token"""
    response = await test_client.get(
        "/api/auth/getUserInfo",
        headers={"Authorization": "Bearer invalid_token_string"}
    )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_expired_token(test_client: AsyncClient):
    """测试过期 Token"""
    from opentask.jwt_utils import create_access_token
    from datetime import timedelta

    # 创建一个已过期的 token（过期时间设为过去）
    expired_token = create_access_token(
        data={"sub": "testuser"},
        expires_delta=timedelta(hours=-24)  # 24小时前过期
    )

    response = await test_client.get(
        "/api/auth/getUserInfo",
        headers={"Authorization": f"Bearer {expired_token}"}
    )

    # 应该返回 401 或 403
    assert response.status_code in [401, 403]


# ============================================================================
# 权限检查测试
# ============================================================================

@pytest.mark.asyncio
async def test_admin_access(test_client: AsyncClient, admin_token):
    """测试管理员权限访问"""
    # 假设有需要管理员权限的端点
    response = await test_client.get(
        "/api/auth/getUserInfo",
        headers={"Authorization": f"Bearer {admin_token}"}
    )

    assert response.status_code == 200


@pytest.mark.asyncio
async def test_regular_user_access(test_client: AsyncClient, test_token):
    """测试普通用户访问"""
    response = await test_client.get(
        "/api/auth/getUserInfo",
        headers={"Authorization": f"Bearer {test_token}"}
    )

    assert response.status_code == 200


# ============================================================================
# 错误处理测试
# ============================================================================

@pytest.mark.asyncio
async def test_malformed_jwt(test_client: AsyncClient):
    """测试格式错误的 JWT"""
    response = await test_client.get(
        "/api/auth/getUserInfo",
        headers={"Authorization": "Bearer not.a.valid.jwt"}
    )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_token_without_bearer_prefix(test_client: AsyncClient, test_token):
    """测试没有 Bearer 前缀的 Token"""
    response = await test_client.get(
        "/api/auth/getUserInfo",
        headers={"Authorization": test_token}  # 缺少 "Bearer " 前缀
    )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_empty_token(test_client: AsyncClient):
    """测试空 Token"""
    response = await test_client.get(
        "/api/auth/getUserInfo",
        headers={"Authorization": "Bearer "}
    )

    assert response.status_code == 401


# ============================================================================
# 多端点认证测试
# ============================================================================

@pytest.mark.asyncio
async def test_authentication_on_multiple_endpoints(test_client: AsyncClient, test_token):
    """测试多个端点的认证"""
    endpoints = [
        "/api/auth/getUserInfo",
    ]

    for endpoint in endpoints:
        response = await test_client.get(
            endpoint,
            headers={"Authorization": f"Bearer {test_token}"}
        )
        # 所有端点都应该成功或至少不返回 401
        assert response.status_code != 401, f"Failed for endpoint: {endpoint}"


# ============================================================================
# Token 刷新测试
# ============================================================================

@pytest.mark.asyncio
async def test_token_refresh_not_implemented(test_client: AsyncClient):
    """测试 Token 刷新（当前未实现）"""
    # 当前 refresh token 功能未实现
    # 这个测试预留用于未来实现
    pass


# ============================================================================
# 并发请求测试
# ============================================================================

@pytest.mark.asyncio
async def test_concurrent_requests_with_same_token(test_client: AsyncClient, test_token):
    """测试使用同一 Token 的并发请求"""
    import asyncio

    async def make_request():
        return await test_client.get(
            "/api/auth/getUserInfo",
            headers={"Authorization": f"Bearer {test_token}"}
        )

    # 并发发送10个请求
    responses = await asyncio.gather(*[make_request() for _ in range(10)])

    # 所有请求都应该成功
    for response in responses:
        assert response.status_code == 200
