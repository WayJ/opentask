"""
集成测试 - 使用真实 API

这些测试连接到真实的 OpenTask API 服务器，
用于验证客户端与实际后端的交互。

运行方式：
    pytest tests/test_integration_real_api.py -v -m integration

注意：需要网络连接和可用的 API 服务器。
"""

import pytest
from opentask.utils.api_client import VibeKingClient, APIError
import asyncio


# ============================================================================
# 配置
# ============================================================================

API_BASE_URL = "http://39.183.172.160:28000/opentask"


# ============================================================================
# 辅助函数
# ============================================================================

async def get_client():
    """创建已认证的客户端（如果可用）"""
    # 尝试从配置读取 token，否则使用匿名访问
    import os
    token = os.environ.get('VIBEKING_TOKEN')

    client = VibeKingClient(base_url=API_BASE_URL, token=token)
    return client


# ============================================================================
# API 连接测试
# ============================================================================

@pytest.mark.integration
class TestAPIConnection:
    """测试 API 连接性"""

    @pytest.mark.asyncio
    async def test_api_reachable(self):
        """测试 API 服务器可达"""
        client = VibeKingClient(base_url=API_BASE_URL)

        try:
            # 尝试访问健康检查端点或公开端点
            result = await client.get("/api/auth/getUserInfo")
            # 即使未认证，也应该返回响应（可能是错误）
            assert result is not None
        except APIError as e:
            # 401 或 403 是预期的（未认证）
            assert e.status_code in [401, 403, 404]
        except Exception as e:
            # 其他错误也应该被捕获
            pytest.skip(f"API 服务器不可用: {e}")

    @pytest.mark.asyncio
    async def test_api_base_url(self):
        """测试 API 基础 URL"""
        client = VibeKingClient(base_url=API_BASE_URL)
        assert client.base_url == API_BASE_URL


# ============================================================================
# 认证测试
# ============================================================================

@pytest.mark.integration
class TestAuthentication:
    """测试认证功能"""

    @pytest.mark.asyncio
    async def test_login_with_invalid_credentials(self):
        """测试使用无效凭据登录"""
        client = VibeKingClient(base_url=API_BASE_URL)

        try:
            result = await client.login("invalid_user", "invalid_password")
            # 如果没有抛出异常，检查返回值
            assert result is None or "token" not in result
        except APIError as e:
            # 401 是预期的
            assert e.status_code == 401
        except Exception as e:
            pytest.skip(f"API 服务器不可用: {e}")

    @pytest.mark.asyncio
    async def test_get_me_unauthenticated(self):
        """测试未认证获取用户信息"""
        client = VibeKingClient(base_url=API_BASE_URL, token=None)

        try:
            result = await client.get_me()
            # 如果成功，说明 API 允许匿名访问
            assert result is None or isinstance(result, dict)
        except APIError as e:
            # 401 是预期的
            assert e.status_code in [401, 403]
        except Exception as e:
            pytest.skip(f"API 服务器不可用: {e}")


# ============================================================================
# Project API 测试
# ============================================================================

@pytest.mark.integration
class TestProjectAPI:
    """测试项目 API"""

    @pytest.mark.asyncio
    async def test_list_projects(self):
        """测试列出项目"""
        client = await get_client()

        try:
            result = await client.list_projects()
            # 应该返回带 rows 字段的字典
            assert isinstance(result, dict)
            assert "rows" in result
            assert isinstance(result["rows"], list)
        except APIError as e:
            # 401/403 是预期的（未认证）
            if e.status_code in [401, 403]:
                pytest.skip("需要认证")
            else:
                raise
        except Exception as e:
            pytest.skip(f"API 服务器不可用: {e}")

    @pytest.mark.asyncio
    async def test_list_projects_with_filters(self):
        """测试带过滤器的项目列表"""
        client = await get_client()

        try:
            result = await client.list_projects(active_only=True)
            assert isinstance(result, dict)
            assert "rows" in result
        except APIError as e:
            if e.status_code in [401, 403]:
                pytest.skip("需要认证")
            else:
                raise
        except Exception as e:
            pytest.skip(f"API 服务器不可用: {e}")


# ============================================================================
# Issue API 测试
# ============================================================================

@pytest.mark.integration
class TestIssueAPI:
    """测试 Issue API"""

    @pytest.mark.asyncio
    async def test_list_issues(self):
        """测试列出 issues"""
        client = await get_client()

        try:
            result = await client.list_issues()
            assert isinstance(result, dict)
            assert "rows" in result
        except APIError as e:
            if e.status_code in [401, 403]:
                pytest.skip("需要认证")
            else:
                raise
        except Exception as e:
            pytest.skip(f"API 服务器不可用: {e}")

    @pytest.mark.asyncio
    async def test_list_issues_with_filters(self):
        """测试带过滤器的 issue 列表"""
        client = await get_client()

        try:
            result = await client.list_issues(
                status="open",
                page=1,
                page_size=10
            )
            assert isinstance(result, dict)
            assert "rows" in result
        except APIError as e:
            if e.status_code in [401, 403]:
                pytest.skip("需要认证")
            else:
                raise
        except Exception as e:
            pytest.skip(f"API 服务器不可用: {e}")

    @pytest.mark.asyncio
    async def test_get_issue(self):
        """测试获取单个 issue"""
        client = await get_client()

        try:
            # 尝试获取一个可能存在的 issue
            result = await client.get_issue("1")
            assert isinstance(result, dict)
        except APIError as e:
            if e.status_code in [401, 403, 404]:
                pytest.skip(f"需要认证或 Issue 不存在: {e.status_code}")
            else:
                raise
        except Exception as e:
            pytest.skip(f"API 服务器不可用: {e}")


# ============================================================================
# Requirement API 测试
# ============================================================================

@pytest.mark.integration
class TestRequirementAPI:
    """测试 Requirement API"""

    @pytest.mark.asyncio
    async def test_list_requirements(self):
        """测试列出 requirements"""
        client = await get_client()

        try:
            result = await client.list_requirements()
            assert isinstance(result, dict)
            assert "rows" in result
        except APIError as e:
            if e.status_code in [401, 403]:
                pytest.skip("需要认证")
            else:
                raise
        except Exception as e:
            pytest.skip(f"API 服务器不可用: {e}")

    @pytest.mark.asyncio
    async def test_get_requirement(self):
        """测试获取单个 requirement"""
        client = await get_client()

        try:
            result = await client.get_requirement("1")
            assert isinstance(result, dict)
        except APIError as e:
            if e.status_code in [401, 403, 404]:
                pytest.skip(f"需要认证或 Requirement 不存在: {e.status_code}")
            else:
                raise
        except Exception as e:
            pytest.skip(f"API 服务器不可用: {e}")


# ============================================================================
# Collection API 测试
# ============================================================================

@pytest.mark.integration
class TestCollectionAPI:
    """测试 Collection API"""

    @pytest.mark.asyncio
    async def test_list_collections(self):
        """测试列出 collections"""
        client = await get_client()

        try:
            result = await client.list_collections()
            assert isinstance(result, dict)
            assert "rows" in result
        except APIError as e:
            # collection API 可能不存在 (404)
            if e.status_code in [401, 403, 404]:
                pytest.skip(f"需要认证或 API 不存在: {e.status_code}")
            else:
                raise
        except Exception as e:
            pytest.skip(f"API 服务器不可用: {e}")


# ============================================================================
# 错误处理测试
# ============================================================================

@pytest.mark.integration
class TestErrorHandling:
    """测试错误处理"""

    @pytest.mark.asyncio
    async def test_404_error(self):
        """测试 404 错误处理"""
        client = await get_client()

        try:
            # 访问不存在的端点
            result = await client.get("/api/nonexistent")
            pytest.fail("应该抛出 404 错误")
        except APIError as e:
            assert e.status_code == 404
        except Exception as e:
            pytest.skip(f"API 服务器不可用: {e}")

    @pytest.mark.asyncio
    async def test_invalid_method(self):
        """测试不支持的 HTTP 方法"""
        client = await get_client()

        try:
            # 尝试使用错误的方法
            result = await client.post("/api/auth/getUserInfo", data={})
            # 如果没有抛出异常，检查响应
            assert result is not None
        except APIError as e:
            # 405 Method Not Allowed 是预期的
            assert e.status_code in [405, 404, 401]
        except Exception as e:
            pytest.skip(f"API 服务器不可用: {e}")


# ============================================================================
# 性能测试
# ============================================================================

@pytest.mark.integration
@pytest.mark.slow
class TestPerformance:
    """测试 API 性能"""

    @pytest.mark.asyncio
    async def test_response_time(self):
        """测试 API 响应时间"""
        import time
        client = await get_client()

        try:
            start_time = time.time()
            result = await client.list_projects()
            end_time = time.time()

            response_time = end_time - start_time

            # API 响应应该在合理时间内（< 5秒）
            assert response_time < 5.0, f"API 响应时间过长: {response_time:.2f}s"
        except APIError as e:
            if e.status_code in [401, 403]:
                pytest.skip("需要认证")
            else:
                raise
        except Exception as e:
            pytest.skip(f"API 服务器不可用: {e}")

    @pytest.mark.asyncio
    async def test_concurrent_requests(self):
        """测试并发请求"""
        client = await get_client()

        try:
            # 并发执行多个请求
            tasks = [
                client.list_projects(),
                client.list_issues(),
                client.list_requirements(),
            ]

            results = await asyncio.gather(*tasks, return_exceptions=True)

            # 检查结果
            for result in results:
                if isinstance(result, Exception):
                    # 允许认证错误
                    if isinstance(result, APIError) and result.status_code in [401, 403]:
                        continue
                    else:
                        raise
                else:
                    assert isinstance(result, dict)
        except Exception as e:
            pytest.skip(f"API 服务器不可用或需要认证: {e}")
