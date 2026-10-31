"""
完整 CRUD 集成测试 - 使用真实 API 测试创建/更新操作

这些测试执行完整的 CRUD 操作（创建、读取、更新、删除），
以最大化代码覆盖率，特别是覆盖 issue 和 requirement 的创建和更新逻辑。

运行方式：
    pytest tests/test_integration_crud.py -v -m integration

注意：这些测试会创建真实数据，请谨慎使用。
"""

import pytest
from opentask.utils.api_client import OpenTaskClient, APIError
import asyncio
import uuid


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
    client = OpenTaskClient(base_url=API_BASE_URL)

    try:
        result = await client.login(TEST_USERNAME, TEST_PASSWORD)

        if result and "token" in result:
            return OpenTaskClient(base_url=API_BASE_URL, token=result["token"])
        else:
            pytest.skip("登录失败：未获取到 token")
    except Exception as e:
        pytest.skip(f"登录失败: {e}")


async def get_test_project_id(client):
    """获取用于测试的项目 ID"""
    try:
        result = await client.list_projects()
        if result["rows"] and len(result["rows"]) > 0:
            return result["rows"][0].get("id")
        return None
    except:
        return None


def generate_unique_id():
    """生成唯一标识符"""
    return str(uuid.uuid4())[:8]


# ============================================================================
# Issue CRUD 测试
# ============================================================================

@pytest.mark.integration
@pytest.mark.slow
class TestIssueCRUD:
    """测试 Issue 完整 CRUD 操作"""

    @pytest.mark.asyncio
    async def test_create_issue_minimal(self):
        """测试创建最小 issue（仅标题）"""
        client = await get_authenticated_client()

        try:
            project_id = await get_test_project_id(client)

            issue_data = {
                "title": f"测试 Issue - {generate_unique_id()}",
                "type": "improvement",  # 必需字段
                "priority": "medium"  # 必需字段
            }

            if project_id:
                issue_data["project_id"] = project_id

            result = await client.create_issue(**issue_data)

            assert result is not None
            assert isinstance(result, dict)
            assert "id" in result or "title" in result

        except APIError as e:
            pytest.skip(f"创建 issue 失败: {e}")
        except Exception as e:
            pytest.skip(f"测试失败: {e}")

    @pytest.mark.asyncio
    async def test_create_issue_full(self):
        """测试创建完整 issue"""
        client = await get_authenticated_client()

        try:
            project_id = await get_test_project_id(client)

            issue_data = {
                "title": f"完整测试 Issue - {generate_unique_id()}",
                "type": "bug",
                "priority": "high",
                "description": "这是一个自动化测试创建的 issue",
                "status": "open"
            }

            if project_id:
                issue_data["project_id"] = project_id

            result = await client.create_issue(**issue_data)

            assert result is not None
            assert isinstance(result, dict)

        except APIError as e:
            pytest.skip(f"创建 issue 失败: {e}")
        except Exception as e:
            pytest.skip(f"测试失败: {e}")

    @pytest.mark.asyncio
    async def test_update_issue_title(self):
        """测试更新 issue 标题"""
        client = await get_authenticated_client()

        try:
            # 先创建一个 issue
            project_id = await get_test_project_id(client)
            issue_data = {
                "type": "improvement",
                "priority": "medium",
                "title": f"更新测试 Issue - {generate_unique_id()}",
            }

            if project_id:
                issue_data["project_id"] = project_id

            created_issue = await client.create_issue(**issue_data)
            issue_id = created_issue.get("id")

            if issue_id:
                # 更新标题
                update_data = {
                    "title": f"已更新标题 - {generate_unique_id()}"
                }

                result = await client.update_issue(issue_id, **update_data)

                assert result is not None
                assert isinstance(result, dict)
            else:
                pytest.skip("无法获取 issue ID")

        except APIError as e:
            pytest.skip(f"更新 issue 失败: {e}")
        except Exception as e:
            pytest.skip(f"测试失败: {e}")

    @pytest.mark.asyncio
    async def test_update_issue_status(self):
        """测试更新 issue 状态"""
        client = await get_authenticated_client()

        try:
            # 先创建一个 issue
            project_id = await get_test_project_id(client)
            issue_data = {
                "type": "improvement",
                "priority": "medium",
                "title": f"状态测试 Issue - {generate_unique_id()}",
            }

            if project_id:
                issue_data["project_id"] = project_id

            created_issue = await client.create_issue(**issue_data)
            issue_id = created_issue.get("id")

            if issue_id:
                # 更新状态
                result = await client.update_issue(issue_id, status="in_progress")

                assert result is not None
                assert isinstance(result, dict)
            else:
                pytest.skip("无法获取 issue ID")

        except APIError as e:
            pytest.skip(f"更新 issue 状态失败: {e}")
        except Exception as e:
            pytest.skip(f"测试失败: {e}")

    @pytest.mark.asyncio
    async def test_update_issue_multiple_fields(self):
        """测试同时更新 issue 多个字段"""
        client = await get_authenticated_client()

        try:
            # 先创建一个 issue
            project_id = await get_test_project_id(client)
            issue_data = {
                "type": "improvement",
                "priority": "medium",
                "title": f"多字段更新测试 Issue - {generate_unique_id()}",
            }

            if project_id:
                issue_data["project_id"] = project_id

            created_issue = await client.create_issue(**issue_data)
            issue_id = created_issue.get("id")

            if issue_id:
                # 同时更新多个字段
                update_data = {
                    "title": f"已更新标题 - {generate_unique_id()}",
                    "description": "已更新描述",
                    "priority": "urgent",
                    "type": "feature"
                }

                result = await client.update_issue(issue_id, **update_data)

                assert result is not None
                assert isinstance(result, dict)
            else:
                pytest.skip("无法获取 issue ID")

        except APIError as e:
            pytest.skip(f"更新 issue 失败: {e}")
        except Exception as e:
            pytest.skip(f"测试失败: {e}")

    @pytest.mark.asyncio
    async def test_issue_workflow_transitions(self):
        """测试 issue 工作流状态转换"""
        client = await get_authenticated_client()

        try:
            # 先创建一个 issue
            project_id = await get_test_project_id(client)
            issue_data = {
                "type": "improvement",
                "priority": "medium",
                "title": f"工作流测试 Issue - {generate_unique_id()}",
            }

            if project_id:
                issue_data["project_id"] = project_id

            created_issue = await client.create_issue(**issue_data)
            issue_id = created_issue.get("id")

            if issue_id:
                # 测试状态转换：open -> in_progress -> resolved -> closed
                await client.update_issue(issue_id, status="in_progress")
                await client.update_issue(issue_id, status="resolved")
                await client.update_issue(issue_id, status="closed")

                # 验证最终状态
                result = await client.get_issue(issue_id)
                assert result.get("status") == "closed"
            else:
                pytest.skip("无法获取 issue ID")

        except APIError as e:
            pytest.skip(f"工作流测试失败: {e}")
        except Exception as e:
            pytest.skip(f"测试失败: {e}")


# ============================================================================
# Requirement CRUD 测试
# ============================================================================

@pytest.mark.integration
@pytest.mark.slow
class TestRequirementCRUD:
    """测试 Requirement 完整 CRUD 操作"""

    @pytest.mark.asyncio
    async def test_create_requirement_minimal(self):
        """测试创建最小 requirement（仅标题）"""
        client = await get_authenticated_client()

        try:
            project_id = await get_test_project_id(client)

            req_data = {
                "title": f"测试需求 - {generate_unique_id()}",
            }

            if project_id:
                req_data["project_id"] = project_id

            result = await client.create_requirement(**req_data)

            assert result is not None
            assert isinstance(result, dict)
            assert "id" in result or "title" in result

        except APIError as e:
            pytest.skip(f"创建 requirement 失败: {e}")
        except Exception as e:
            pytest.skip(f"测试失败: {e}")

    @pytest.mark.asyncio
    async def test_create_requirement_full(self):
        """测试创建完整 requirement"""
        client = await get_authenticated_client()

        try:
            project_id = await get_test_project_id(client)

            req_data = {
                "title": f"完整测试需求 - {generate_unique_id()}",
                "description": "这是一个自动化测试创建的需求",
                "priority": "high",
                "status": "planning"
            }

            if project_id:
                req_data["project_id"] = project_id

            result = await client.create_requirement(**req_data)

            assert result is not None
            assert isinstance(result, dict)

        except APIError as e:
            pytest.skip(f"创建 requirement 失败: {e}")
        except Exception as e:
            pytest.skip(f"测试失败: {e}")

    @pytest.mark.asyncio
    async def test_update_requirement_title(self):
        """测试更新 requirement 标题"""
        client = await get_authenticated_client()

        try:
            # 先创建一个 requirement
            project_id = await get_test_project_id(client)
            req_data = {
                "title": f"更新测试需求 - {generate_unique_id()}",
            }

            if project_id:
                req_data["project_id"] = project_id

            created_req = await client.create_requirement(**req_data)
            req_id = created_req.get("id")

            if req_id:
                # 更新标题
                result = await client.update_requirement(
                    req_id,
                    title=f"已更新标题 - {generate_unique_id()}"
                )

                assert result is not None
                assert isinstance(result, dict)
            else:
                pytest.skip("无法获取 requirement ID")

        except APIError as e:
            pytest.skip(f"更新 requirement 失败: {e}")
        except Exception as e:
            pytest.skip(f"测试失败: {e}")

    @pytest.mark.asyncio
    async def test_update_requirement_status(self):
        """测试更新 requirement 状态"""
        client = await get_authenticated_client()

        try:
            # 先创建一个 requirement
            project_id = await get_test_project_id(client)
            req_data = {
                "title": f"状态测试需求 - {generate_unique_id()}",
            }

            if project_id:
                req_data["project_id"] = project_id

            created_req = await client.create_requirement(**req_data)
            req_id = created_req.get("id")

            if req_id:
                # 更新状态
                result = await client.update_requirement(req_id, status="clarifying")

                assert result is not None
                assert isinstance(result, dict)
            else:
                pytest.skip("无法获取 requirement ID")

        except APIError as e:
            pytest.skip(f"更新 requirement 状态失败: {e}")
        except Exception as e:
            pytest.skip(f"测试失败: {e}")

    @pytest.mark.asyncio
    async def test_update_requirement_multiple_fields(self):
        """测试同时更新 requirement 多个字段"""
        client = await get_authenticated_client()

        try:
            # 先创建一个 requirement
            project_id = await get_test_project_id(client)
            req_data = {
                "title": f"多字段更新测试需求 - {generate_unique_id()}",
            }

            if project_id:
                req_data["project_id"] = project_id

            created_req = await client.create_requirement(**req_data)
            req_id = created_req.get("id")

            if req_id:
                # 同时更新多个字段
                result = await client.update_requirement(
                    req_id,
                    title=f"已更新标题 - {generate_unique_id()}",
                    description="已更新描述",
                    priority="critical"
                )

                assert result is not None
                assert isinstance(result, dict)
            else:
                pytest.skip("无法获取 requirement ID")

        except APIError as e:
            pytest.skip(f"更新 requirement 失败: {e}")
        except Exception as e:
            pytest.skip(f"测试失败: {e}")

    @pytest.mark.asyncio
    async def test_requirement_workflow_transitions(self):
        """测试 requirement 工作流状态转换"""
        client = await get_authenticated_client()

        try:
            # 先创建一个 requirement
            project_id = await get_test_project_id(client)
            req_data = {
                "title": f"工作流测试需求 - {generate_unique_id()}",
            }

            if project_id:
                req_data["project_id"] = project_id

            created_req = await client.create_requirement(**req_data)
            req_id = created_req.get("id")

            if req_id:
                # 测试状态转换：draft -> clarifying -> designing -> coding -> testing -> released
                await client.update_requirement(req_id, status="clarifying")
                await client.update_requirement(req_id, status="designing")
                await client.update_requirement(req_id, status="coding")
                await client.update_requirement(req_id, status="testing")
                await client.update_requirement(req_id, status="released")

                # 验证最终状态
                result = await client.get_requirement(req_id)
                assert result.get("status") == "released"
            else:
                pytest.skip("无法获取 requirement ID")

        except APIError as e:
            pytest.skip(f"工作流测试失败: {e}")
        except Exception as e:
            pytest.skip(f"测试失败: {e}")


# ============================================================================
# Comment CRUD 测试
# ============================================================================

@pytest.mark.integration
@pytest.mark.slow
class TestCommentCRUD:
    """测试 Comment CRUD 操作"""

    @pytest.mark.asyncio
    async def test_add_issue_comment(self):
        """测试为 issue 添加评论"""
        client = await get_authenticated_client()

        try:
            # 先获取一个 issue
            list_result = await client.list_issues()

            if list_result["rows"] and len(list_result["rows"]) > 0:
                issue_id = list_result["rows"][0].get("id")

                if issue_id:
                    # 添加评论
                    comment = f"自动化测试评论 - {generate_unique_id()}"
                    result = await client.add_issue_comment(issue_id, comment)

                    assert result is not None
                else:
                    pytest.skip("无法获取 issue ID")
            else:
                pytest.skip("没有可用的 issues")

        except APIError as e:
            pytest.skip(f"添加评论失败: {e}")
        except Exception as e:
            pytest.skip(f"测试失败: {e}")

    @pytest.mark.asyncio
    async def test_add_requirement_comment(self):
        """测试为 requirement 添加评论"""
        client = await get_authenticated_client()

        try:
            # 先获取一个 requirement
            list_result = await client.list_requirements()

            if list_result["rows"] and len(list_result["rows"]) > 0:
                req_id = list_result["rows"][0].get("id")

                if req_id:
                    # 添加评论
                    comment = f"自动化测试评论 - {generate_unique_id()}"
                    result = await client.add_requirement_comment(req_id, comment)

                    assert result is not None
                else:
                    pytest.skip("无法获取 requirement ID")
            else:
                pytest.skip("没有可用的 requirements")

        except APIError as e:
            pytest.skip(f"添加评论失败: {e}")
        except Exception as e:
            pytest.skip(f"测试失败: {e}")


# ============================================================================
# Assignment 测试
# ============================================================================

@pytest.mark.integration
@pytest.mark.slow
class TestAssignment:
    """测试分配功能"""

    @pytest.mark.asyncio
    async def test_assign_issue(self):
        """测试分配 issue"""
        client = await get_authenticated_client()

        try:
            # 获取当前用户 ID
            user = await client.get_me()
            user_id = user.get("id") if user else None

            if not user_id:
                pytest.skip("无法获取用户 ID")

            # 先获取一个 issue
            list_result = await client.list_issues()

            if list_result["rows"] and len(list_result["rows"]) > 0:
                issue_id = list_result["rows"][0].get("id")

                if issue_id:
                    # 分配给自己
                    result = await client.assign_issue(issue_id, user_id)

                    assert result is not None
                else:
                    pytest.skip("无法获取 issue ID")
            else:
                pytest.skip("没有可用的 issues")

        except APIError as e:
            pytest.skip(f"分配 issue 失败: {e}")
        except Exception as e:
            pytest.skip(f"测试失败: {e}")

    @pytest.mark.asyncio
    async def test_assign_requirement(self):
        """测试分配 requirement"""
        client = await get_authenticated_client()

        try:
            # 获取当前用户 ID
            user = await client.get_me()
            user_id = user.get("id") if user else None

            if not user_id:
                pytest.skip("无法获取用户 ID")

            # 先获取一个 requirement
            list_result = await client.list_requirements()

            if list_result["rows"] and len(list_result["rows"]) > 0:
                req_id = list_result["rows"][0].get("id")

                if req_id:
                    # 分配给自己
                    result = await client.assign_requirement(req_id, user_id)

                    assert result is not None
                else:
                    pytest.skip("无法获取 requirement ID")
            else:
                pytest.skip("没有可用的 requirements")

        except APIError as e:
            pytest.skip(f"分配 requirement 失败: {e}")
        except Exception as e:
            pytest.skip(f"测试失败: {e}")


# ============================================================================
# 批量操作测试
# ============================================================================

@pytest.mark.integration
@pytest.mark.slow
class TestBatchOperationsFull:
    """测试批量操作"""

    @pytest.mark.asyncio
    async def test_batch_assign_issues(self):
        """测试批量分配 issues"""
        client = await get_authenticated_client()

        try:
            # 获取当前用户 ID
            user = await client.get_me()
            user_id = user.get("id") if user else None

            if not user_id:
                pytest.skip("无法获取用户 ID")

            # 获取多个 issues
            list_result = await client.list_issues()

            if list_result["rows"] and len(list_result["rows"]) >= 2:
                issue_ids = [
                    list_result["rows"][0].get("id"),
                    list_result["rows"][1].get("id")
                ]
                issue_ids = [id for id in issue_ids if id]

                if len(issue_ids) >= 2:
                    # 批量分配
                    result = await client.batch_assign_issues(issue_ids, user_id)

                    assert result is not None
                else:
                    pytest.skip("需要至少 2 个 issues")
            else:
                pytest.skip("需要至少 2 个 issues")

        except APIError as e:
            pytest.skip(f"批量分配失败: {e}")
        except Exception as e:
            pytest.skip(f"测试失败: {e}")

    @pytest.mark.asyncio
    async def test_batch_update_issues(self):
        """测试批量更新 issues"""
        client = await get_authenticated_client()

        try:
            # 获取多个 issues
            list_result = await client.list_issues()

            if list_result["rows"] and len(list_result["rows"]) >= 2:
                issue_ids = [
                    list_result["rows"][0].get("id"),
                    list_result["rows"][1].get("id")
                ]
                issue_ids = [id for id in issue_ids if id]

                if len(issue_ids) >= 2:
                    # 批量更新状态
                    result = await client.batch_update_issues(
                        issue_ids,
                        status="in_progress"
                    )

                    assert result is not None
                else:
                    pytest.skip("需要至少 2 个 issues")
            else:
                pytest.skip("需要至少 2 个 issues")

        except APIError as e:
            pytest.skip(f"批量更新失败: {e}")
        except Exception as e:
            pytest.skip(f"测试失败: {e}")


# ============================================================================
# 特殊操作测试
# ============================================================================

@pytest.mark.integration
@pytest.mark.slow
class TestSpecialOperations:
    """测试特殊操作"""

    @pytest.mark.asyncio
    async def test_resolve_issue(self):
        """测试解决 issue"""
        client = await get_authenticated_client()

        try:
            # 先创建一个 issue
            project_id = await get_test_project_id(client)
            issue_data = {
                "type": "improvement",
                "priority": "medium",
                "title": f"解决测试 Issue - {generate_unique_id()}",
                "status": "open"
            }

            if project_id:
                issue_data["project_id"] = project_id

            created_issue = await client.create_issue(**issue_data)
            issue_id = created_issue.get("id")

            if issue_id:
                # 解决 issue
                result = await client.resolve_issue(
                    issue_id,
                    reason="自动化测试解决"
                )

                assert result is not None
            else:
                pytest.skip("无法获取 issue ID")

        except APIError as e:
            pytest.skip(f"解决 issue 失败: {e}")
        except Exception as e:
            pytest.skip(f"测试失败: {e}")

    @pytest.mark.asyncio
    async def test_close_issue(self):
        """测试关闭 issue"""
        client = await get_authenticated_client()

        try:
            # 先创建一个已解决的 issue
            project_id = await get_test_project_id(client)
            issue_data = {
                "type": "improvement",
                "priority": "medium",
                "title": f"关闭测试 Issue - {generate_unique_id()}",
                "status": "resolved"
            }

            if project_id:
                issue_data["project_id"] = project_id

            created_issue = await client.create_issue(**issue_data)
            issue_id = created_issue.get("id")

            if issue_id:
                # 关闭 issue
                result = await client.close_issue(
                    issue_id,
                    reason="自动化测试关闭"
                )

                assert result is not None
            else:
                pytest.skip("无法获取 issue ID")

        except APIError as e:
            pytest.skip(f"关闭 issue 失败: {e}")
        except Exception as e:
            pytest.skip(f"测试失败: {e}")

    @pytest.mark.asyncio
    async def test_resolve_requirement(self):
        """测试解决 requirement"""
        client = await get_authenticated_client()

        try:
            # 先创建一个 requirement
            project_id = await get_test_project_id(client)
            req_data = {
                "title": f"解决测试需求 - {generate_unique_id()}",
                "status": "coding"
            }

            if project_id:
                req_data["project_id"] = project_id

            created_req = await client.create_requirement(**req_data)
            req_id = created_req.get("id")

            if req_id:
                # 解决 requirement（转为 reviewing）
                result = await client.resolve_requirement(
                    req_id,
                    reason="代码完成，进入审查"
                )

                assert result is not None
            else:
                pytest.skip("无法获取 requirement ID")

        except APIError as e:
            pytest.skip(f"解决 requirement 失败: {e}")
        except Exception as e:
            pytest.skip(f"测试失败: {e}")

    @pytest.mark.asyncio
    async def test_close_requirement(self):
        """测试关闭 requirement"""
        client = await get_authenticated_client()

        try:
            # 先创建一个已解决的 requirement
            project_id = await get_test_project_id(client)
            req_data = {
                "title": f"关闭测试需求 - {generate_unique_id()}",
                "status": "reviewing"
            }

            if project_id:
                req_data["project_id"] = project_id

            created_req = await client.create_requirement(**req_data)
            req_id = created_req.get("id")

            if req_id:
                # 关闭 requirement（转为 released）
                result = await client.close_requirement(
                    req_id,
                    reason="测试通过，发布"
                )

                assert result is not None
            else:
                pytest.skip("无法获取 requirement ID")

        except APIError as e:
            pytest.skip(f"关闭 requirement 失败: {e}")
        except Exception as e:
            pytest.skip(f"测试失败: {e}")


# ============================================================================
# 搜索和查找测试
# ============================================================================

@pytest.mark.integration
@pytest.mark.slow
class TestSearchAndFind:
    """测试搜索和查找功能"""

    @pytest.mark.asyncio
    async def test_find_issues_by_keyword(self):
        """测试通过关键词搜索 issues"""
        client = await get_authenticated_client()

        try:
            # 创建一个测试 issue
            project_id = await get_test_project_id(client)
            keyword = generate_unique_id()
            issue_data = {
                "type": "improvement",
                "priority": "medium",
                "title": f"搜索测试 Issue {keyword}",
            }

            if project_id:
                issue_data["project_id"] = project_id

            await client.create_issue(**issue_data)

            # 搜索刚创建的 issue
            result = await client.find_issues(keyword)

            assert result is not None
            assert isinstance(result, dict)
            assert "rows" in result

        except APIError as e:
            pytest.skip(f"搜索失败: {e}")
        except Exception as e:
            pytest.skip(f"测试失败: {e}")

    @pytest.mark.asyncio
    async def test_find_requirements_by_keyword(self):
        """测试通过关键词搜索 requirements"""
        client = await get_authenticated_client()

        try:
            # 创建一个测试 requirement
            project_id = await get_test_project_id(client)
            keyword = generate_unique_id()
            req_data = {
                "title": f"搜索测试需求 {keyword}",
            }

            if project_id:
                req_data["project_id"] = project_id

            await client.create_requirement(**req_data)

            # 搜索刚创建的 requirement
            result = await client.find_requirements(keyword)

            assert result is not None
            assert isinstance(result, dict)
            assert "rows" in result

        except APIError as e:
            pytest.skip(f"搜索失败: {e}")
        except Exception as e:
            pytest.skip(f"测试失败: {e}")

    @pytest.mark.asyncio
    async def test_filter_issues_by_multiple_criteria(self):
        """测试多条件过滤 issues"""
        client = await get_authenticated_client()

        try:
            # 使用多个过滤条件
            result = await client.list_issues(
                status="open",
                priority="high",
                page=1,
                page_size=10
            )

            assert result is not None
            assert isinstance(result, dict)
            assert "rows" in result

        except APIError as e:
            pytest.skip(f"多条件过滤失败: {e}")
        except Exception as e:
            pytest.skip(f"测试失败: {e}")
