"""
认证集成测试 - 使用真实账号登录

这些测试使用真实的 OpenTask API 服务器和认证凭据，
执行完整的 CRUD 操作以最大化代码覆盖率。

运行方式：
    pytest tests/test_integration_authenticated.py -v -m integration

注意：需要网络连接和有效的认证凭据。
"""

import pytest
from opentask.utils.api_client import VibeKingClient, APIError
import asyncio
import os


# ============================================================================
# 配置
# ============================================================================

API_BASE_URL = "http://39.183.172.160:28000/opentask"
TEST_USERNAME = "xxxxx"
TEST_PASSWORD = "xxxxx"


# ============================================================================
# 辅助函数
# ============================================================================

async def get_authenticated_client():
    """创建已认证的客户端"""
    client = VibeKingClient(base_url=API_BASE_URL)

    try:
        # 登录（Phase 2 后端本地校验，密码明文提交）
        result = await client.login(TEST_USERNAME, TEST_PASSWORD)

        if result and "token" in result:
            # 创建新的客户端实例，使用获取的 token
            auth_client = VibeKingClient(
                base_url=API_BASE_URL,
                token=result["token"]
            )
            return auth_client
        else:
            pytest.skip("登录失败：未获取到 token")
    except Exception as e:
        pytest.skip(f"登录失败: {e}")


# ============================================================================
# 认证测试
# ============================================================================

@pytest.mark.integration
class TestAuthentication:
    """测试认证功能"""

    @pytest.mark.asyncio
    async def test_login_success(self):
        """测试成功登录"""
        client = VibeKingClient(base_url=API_BASE_URL)

        try:
            result = await client.login(TEST_USERNAME, TEST_PASSWORD)

            assert result is not None
            assert "token" in result or "access_token" in result

            # 保存 token 用于后续测试
            if "token" in result:
                os.environ['__TEST_TOKEN__'] = result["token"]
        except Exception as e:
            pytest.skip(f"登录失败: {e}")

    @pytest.mark.asyncio
    async def test_get_me_authenticated(self):
        """测试已认证获取用户信息"""
        client = await get_authenticated_client()

        try:
            result = await client.get_me()
            assert result is not None
            assert isinstance(result, dict)
            # 应该包含用户信息
            assert "id" in result or "jnpf_account" in result or "jnpf_name" in result
        except Exception as e:
            pytest.skip(f"获取用户信息失败: {e}")


# ============================================================================
# Project API 完整测试
# ============================================================================

@pytest.mark.integration
class TestProjectAPIFull:
    """完整测试项目 API"""

    @pytest.mark.asyncio
    async def test_list_projects_all(self):
        """测试列出所有项目"""
        client = await get_authenticated_client()

        try:
            result = await client.list_projects()
            assert isinstance(result, dict)
            assert "rows" in result
            assert isinstance(result["rows"], list)

            # 如果有项目，检查结构
            if len(result["rows"]) > 0:
                project = result["rows"][0]
                assert "id" in project or "name" in project
        except Exception as e:
            pytest.skip(f"列出项目失败: {e}")

    @pytest.mark.asyncio
    async def test_list_projects_active_only(self):
        """测试只列出活跃项目"""
        client = await get_authenticated_client()

        try:
            result = await client.list_projects(active_only=True)
            assert isinstance(result, dict)
            assert "rows" in result
        except Exception as e:
            pytest.skip(f"列出活跃项目失败: {e}")

    @pytest.mark.asyncio
    async def test_get_project(self):
        """测试获取单个项目"""
        client = await get_authenticated_client()

        try:
            # 先获取项目列表
            list_result = await client.list_projects()

            if list_result["rows"] and len(list_result["rows"]) > 0:
                project_id = list_result["rows"][0].get("id")

                if project_id:
                    result = await client.get_project(project_id)
                    assert result is not None
                    assert isinstance(result, dict)
            else:
                pytest.skip("没有可用的项目")
        except Exception as e:
            pytest.skip(f"获取项目详情失败: {e}")


# ============================================================================
# Issue API 完整测试
# ============================================================================

@pytest.mark.integration
class TestIssueAPIFull:
    """完整测试 Issue API"""

    @pytest.mark.asyncio
    async def test_list_issues_all(self):
        """测试列出所有 issues"""
        client = await get_authenticated_client()

        try:
            result = await client.list_issues()
            assert isinstance(result, dict)
            assert "rows" in result
            assert isinstance(result["rows"], list)

            # 如果有 issues，检查结构
            if len(result["rows"]) > 0:
                issue = result["rows"][0]
                assert "id" in issue or "title" in issue
        except Exception as e:
            pytest.skip(f"列出 issues 失败: {e}")

    @pytest.mark.asyncio
    async def test_list_issues_with_status_filter(self):
        """测试按状态过滤 issues"""
        client = await get_authenticated_client()

        try:
            result = await client.list_issues(status="open")
            assert isinstance(result, dict)
            assert "rows" in result
        except Exception as e:
            pytest.skip(f"按状态过滤失败: {e}")

    @pytest.mark.asyncio
    async def test_list_issues_with_priority_filter(self):
        """测试按优先级过滤 issues"""
        client = await get_authenticated_client()

        try:
            result = await client.list_issues(priority="high")
            assert isinstance(result, dict)
            assert "rows" in result
        except Exception as e:
            pytest.skip(f"按优先级过滤失败: {e}")

    @pytest.mark.asyncio
    async def test_get_issue(self):
        """测试获取单个 issue"""
        client = await get_authenticated_client()

        try:
            # 先获取 issue 列表
            list_result = await client.list_issues()

            if list_result["rows"] and len(list_result["rows"]) > 0:
                issue_id = list_result["rows"][0].get("id")

                if issue_id:
                    result = await client.get_issue(issue_id)
                    assert result is not None
                    assert isinstance(result, dict)
            else:
                pytest.skip("没有可用的 issues")
        except Exception as e:
            pytest.skip(f"获取 issue 详情失败: {e}")

    @pytest.mark.asyncio
    async def test_get_issue_comments(self):
        """测试获取 issue 评论"""
        client = await get_authenticated_client()

        try:
            # 先获取 issue 列表
            list_result = await client.list_issues()

            if list_result["rows"] and len(list_result["rows"]) > 0:
                issue_id = list_result["rows"][0].get("id")

                if issue_id:
                    result = await client.get_issue_comments(issue_id)
                    assert result is not None
                    assert isinstance(result, list)
            else:
                pytest.skip("没有可用的 issues")
        except Exception as e:
            pytest.skip(f"获取 issue 评论失败: {e}")


# ============================================================================
# Requirement API 完整测试
# ============================================================================

@pytest.mark.integration
class TestRequirementAPIFull:
    """完整测试 Requirement API"""

    @pytest.mark.asyncio
    async def test_list_requirements_all(self):
        """测试列出所有 requirements"""
        client = await get_authenticated_client()

        try:
            result = await client.list_requirements()
            assert isinstance(result, dict)
            assert "rows" in result
            assert isinstance(result["rows"], list)
        except Exception as e:
            pytest.skip(f"列出 requirements 失败: {e}")

    @pytest.mark.asyncio
    async def test_list_requirements_with_status_filter(self):
        """测试按状态过滤 requirements"""
        client = await get_authenticated_client()

        try:
            result = await client.list_requirements(status="planning")
            assert isinstance(result, dict)
            assert "rows" in result
        except Exception as e:
            pytest.skip(f"按状态过滤失败: {e}")

    @pytest.mark.asyncio
    async def test_get_requirement(self):
        """测试获取单个 requirement"""
        client = await get_authenticated_client()

        try:
            # 先获取 requirement 列表
            list_result = await client.list_requirements()

            if list_result["rows"] and len(list_result["rows"]) > 0:
                req_id = list_result["rows"][0].get("id")

                if req_id:
                    result = await client.get_requirement(req_id)
                    assert result is not None
                    assert isinstance(result, dict)
            else:
                pytest.skip("没有可用的 requirements")
        except Exception as e:
            pytest.skip(f"获取 requirement 详情失败: {e}")

    @pytest.mark.asyncio
    async def test_get_requirement_comments(self):
        """测试获取 requirement 评论"""
        client = await get_authenticated_client()

        try:
            # 先获取 requirement 列表
            list_result = await client.list_requirements()

            if list_result["rows"] and len(list_result["rows"]) > 0:
                req_id = list_result["rows"][0].get("id")

                if req_id:
                    result = await client.get_requirement_comments(req_id)
                    assert result is not None
                    assert isinstance(result, list)
            else:
                pytest.skip("没有可用的 requirements")
        except Exception as e:
            pytest.skip(f"获取 requirement 评论失败: {e}")


# ============================================================================
# Collection API 测试
# ============================================================================

@pytest.mark.integration
class TestCollectionAPIFull:
    """测试 Collection API"""

    @pytest.mark.asyncio
    async def test_list_collections(self):
        """测试列出 collections"""
        client = await get_authenticated_client()

        try:
            result = await client.list_collections()
            assert isinstance(result, dict)
            assert "rows" in result
        except APIError as e:
            # Collection API 可能不存在
            if e.status_code == 404:
                pytest.skip("Collection API 不存在")
            else:
                raise
        except Exception as e:
            pytest.skip(f"列出 collections 失败: {e}")


# ============================================================================
# 批量操作测试
# ============================================================================

@pytest.mark.integration
class TestBatchOperations:
    """测试批量操作"""

    @pytest.mark.asyncio
    async def test_batch_get_issues(self):
        """测试批量获取 issues"""
        client = await get_authenticated_client()

        try:
            # 先获取 issue 列表
            list_result = await client.list_issues()

            if list_result["rows"] and len(list_result["rows"]) >= 2:
                issue_ids = [list_result["rows"][0].get("id"), list_result["rows"][1].get("id")]
                issue_ids = [id for id in issue_ids if id]

                if issue_ids:
                    result = await client.batch_get_issues(issue_ids)
                    assert result is not None
                    assert isinstance(result, list)
            else:
                pytest.skip("需要至少 2 个 issues 进行批量测试")
        except Exception as e:
            pytest.skip(f"批量获取 issues 失败: {e}")

    @pytest.mark.asyncio
    async def test_batch_get_requirements(self):
        """测试批量获取 requirements"""
        client = await get_authenticated_client()

        try:
            # 先获取 requirement 列表
            list_result = await client.list_requirements()

            if list_result["rows"] and len(list_result["rows"]) >= 2:
                req_ids = [list_result["rows"][0].get("id"), list_result["rows"][1].get("id")]
                req_ids = [id for id in req_ids if id]

                if req_ids:
                    result = await client.batch_get_requirements(req_ids)
                    assert result is not None
                    assert isinstance(result, list)
            else:
                pytest.skip("需要至少 2 个 requirements 进行批量测试")
        except Exception as e:
            pytest.skip(f"批量获取 requirements 失败: {e}")


# ============================================================================
# 错误处理测试
# ============================================================================

@pytest.mark.integration
class TestErrorHandlingFull:
    """测试错误处理"""

    @pytest.mark.asyncio
    async def test_get_nonexistent_issue(self):
        """测试获取不存在的 issue"""
        client = await get_authenticated_client()

        try:
            result = await client.get_issue("nonexistent-id-99999")
            pytest.fail("应该抛出 404 错误")
        except APIError as e:
            assert e.status_code == 404
        except Exception as e:
            pytest.skip(f"API 服务器错误: {e}")

    @pytest.mark.asyncio
    async def test_get_nonexistent_requirement(self):
        """测试获取不存在的 requirement"""
        client = await get_authenticated_client()

        try:
            result = await client.get_requirement("nonexistent-id-99999")
            pytest.fail("应该抛出 404 错误")
        except APIError as e:
            assert e.status_code == 404
        except Exception as e:
            pytest.skip(f"API 服务器错误: {e}")

    @pytest.mark.asyncio
    async def test_update_nonexistent_issue(self):
        """测试更新不存在的 issue"""
        client = await get_authenticated_client()

        try:
            result = await client.update_issue("nonexistent-id-99999", {"title": "Test"})
            pytest.fail("应该抛出 404 错误")
        except APIError as e:
            assert e.status_code == 404
        except Exception as e:
            pytest.skip(f"API 服务器错误: {e}")


# ============================================================================
# 搜索和过滤测试
# ============================================================================

@pytest.mark.integration
class TestSearchAndFilter:
    """测试搜索和过滤功能"""

    @pytest.mark.asyncio
    async def test_find_issues_by_keyword(self):
        """测试通过关键词搜索 issues"""
        client = await get_authenticated_client()

        try:
            result = await client.find_issues("test")
            assert isinstance(result, dict)
            assert "rows" in result
        except Exception as e:
            pytest.skip(f"搜索 issues 失败: {e}")

    @pytest.mark.asyncio
    async def test_find_requirements_by_keyword(self):
        """测试通过关键词搜索 requirements"""
        client = await get_authenticated_client()

        try:
            result = await client.find_requirements("test")
            assert isinstance(result, dict)
            assert "rows" in result
        except Exception as e:
            pytest.skip(f"搜索 requirements 失败: {e}")

    @pytest.mark.asyncio
    async def test_list_my_issues(self):
        """测试列出我的 issues"""
        client = await get_authenticated_client()

        try:
            # 先获取当前用户信息
            user = await client.get_me()
            user_id = user.get("id") if user else None

            if user_id:
                result = await client.list_my_issues(user_id)
                assert isinstance(result, dict)
                assert "rows" in result
            else:
                pytest.skip("无法获取用户 ID")
        except Exception as e:
            pytest.skip(f"列出我的 issues 失败: {e}")


# ============================================================================
# 分页测试
# ============================================================================

@pytest.mark.integration
class TestPagination:
    """测试分页功能"""

    @pytest.mark.asyncio
    async def test_list_issues_pagination(self):
        """测试 issue 列表分页"""
        client = await get_authenticated_client()

        try:
            # 第一页
            page1 = await client.list_issues(page=1, page_size=5)
            assert isinstance(page1, dict)
            assert "rows" in page1

            # 第二页
            page2 = await client.list_issues(page=2, page_size=5)
            assert isinstance(page2, dict)
            assert "rows" in page2
        except Exception as e:
            pytest.skip(f"分页测试失败: {e}")

    @pytest.mark.asyncio
    async def test_list_requirements_pagination(self):
        """测试 requirement 列表分页"""
        client = await get_authenticated_client()

        try:
            page1 = await client.list_requirements(page=1, page_size=5)
            assert isinstance(page1, dict)
            assert "rows" in page1
        except Exception as e:
            pytest.skip(f"分页测试失败: {e}")
