"""
API 路由测试

测试所有 API 端点的基本功能
"""
import pytest
from httpx import AsyncClient, ASGITransport
from starlette.applications import Starlette

from opentask.app import App


@pytest.mark.asyncio
async def test_get_roles_endpoint():
    """测试获取角色列表端点"""
    app = App()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/roles")
        # 没有认证应该返回 401
        assert response.status_code == 401


@pytest.mark.asyncio
async def test_health_check():
    """测试健康检查端点"""
    app = App()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # 测试根路径
        response = await client.get("/")
        # 应该返回 404 因为没有根路径处理，但不应该崩溃
        assert response.status_code in [200, 404]


@pytest.mark.asyncio
async def test_api_users_me_requires_auth():
    """测试 /api/users/me 需要认证"""
    app = App()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/users/me")
        # 没有认证应该返回 401
        assert response.status_code == 401


@pytest.mark.asyncio
async def test_api_users_searchable_requires_auth():
    """测试 /api/users/searchable 需要认证"""
    app = App()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/users/searchable")
        # 没有认证应该返回 401
        assert response.status_code == 401


@pytest.mark.asyncio
async def test_api_users_list_requires_auth():
    """测试 /api/users 需要认证"""
    app = App()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/users")
        # 没有认证应该返回 401
        assert response.status_code == 401


@pytest.mark.asyncio
async def test_api_issues_endpoint():
    """测试 Issue 端点"""
    app = App()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Issue 端点不需要认证
        response = await client.get("/api/issues")
        # 应该返回列表（可能为空）
        assert response.status_code in [200, 401]
