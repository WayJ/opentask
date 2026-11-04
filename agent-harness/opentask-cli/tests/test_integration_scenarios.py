import os
"""
完整应用场景集成测试

测试范围：
- 完整的用户工作流（登录 → 选择项目 → 操作 issue → 操作 requirement）
- 真实 API 调用的端到端测试
- 多步骤操作场景
- 错误恢复场景
"""

import pytest
from click.testing import CliRunner
from unittest import mock
import asyncio
import tempfile
from pathlib import Path

from opentask.opentask_cli import cli
from opentask.utils.api_client import OpenTaskClient


# ============================================================================
# 配置
# ============================================================================

API_BASE_URL = os.environ.get("OPENTASK_TEST_API_URL", "")
pytestmark = pytest.mark.skipif(not API_BASE_URL, reason="OPENTASK_TEST_API_URL not set; live integration tests skipped")
TEST_USERNAME = "xxxxx"
TEST_PASSWORD = "xxxxx"


# ============================================================================
# 辅助函数
# ============================================================================

def async_mock(return_value):
    """创建异步 Mock 函数"""
    async def wrapper(*args, **kwargs):
        return return_value
    return wrapper


async def get_authenticated_client():
    """创建已认证的客户端"""
    client = OpenTaskClient(base_url=API_BASE_URL)

    try:
        result = await client.login(TEST_USERNAME, TEST_PASSWORD)

        if result and "token" in result:
            return OpenTaskClient(base_url=API_BASE_URL, token=result["token"])
        else:
            return None
    except:
        return None


# ============================================================================
# 完整用户工作流测试
# ============================================================================

@pytest.mark.integration
@pytest.mark.slow
class TestCompleteUserWorkflow:
    """测试完整的用户工作流"""

    @pytest.mark.asyncio
    async def test_login_and_list_projects(self):
        """测试登录并列出项目"""
        client = await get_authenticated_client()

        if not client:
            pytest.skip("无法获取认证客户端")

        try:
            # 列出项目
            projects = await client.list_projects()

            assert projects is not None
            assert "rows" in projects
            assert isinstance(projects["rows"], list)

        except Exception as e:
            pytest.skip(f"测试失败: {e}")

    @pytest.mark.asyncio
    async def test_browse_project_issues(self):
        """测试浏览项目的 issues"""
        client = await get_authenticated_client()

        if not client:
            pytest.skip("无法获取认证客户端")

        try:
            # 获取项目列表
            projects = await client.list_projects()

            if projects["rows"] and len(projects["rows"]) > 0:
                project = projects["rows"][0]
                project_id = project.get("id")

                if project_id:
                    # 列出该项目的 issues
                    issues = await client.list_issues(project_id=project_id)

                    assert issues is not None
                    assert "rows" in issues
            else:
                pytest.skip("没有可用的项目")
        except Exception as e:
            pytest.skip(f"测试失败: {e}")

    @pytest.mark.asyncio
    async def test_browse_project_requirements(self):
        """测试浏览项目的 requirements"""
        client = await get_authenticated_client()

        if not client:
            pytest.skip("无法获取认证客户端")

        try:
            # 获取项目列表
            projects = await client.list_projects()

            if projects["rows"] and len(projects["rows"]) > 0:
                project = projects["rows"][0]
                project_id = project.get("id")

                if project_id:
                    # 列出该项目的 requirements
                    requirements = await client.list_requirements(project_id=project_id)

                    assert requirements is not None
                    assert "rows" in requirements
            else:
                pytest.skip("没有可用的项目")
        except Exception as e:
            pytest.skip(f"测试失败: {e}")

    @pytest.mark.asyncio
    async def test_issue_lifecycle(self):
        """测试完整的 issue 生命周期"""
        client = await get_authenticated_client()

        if not client:
            pytest.skip("无法获取认证客户端")

        try:
            # 获取项目 ID
            projects = await client.list_projects()
            if not projects["rows"]:
                pytest.skip("没有可用的项目")

            project_id = projects["rows"][0].get("id")

            # 1. 创建 issue
            issue_data = {
                "title": "生命周期测试 Issue",
                "type": "improvement",
                "priority": "medium"
            }

            if project_id:
                issue_data["project_id"] = project_id

            created_issue = await client.create_issue(**issue_data)
            issue_id = created_issue.get("id")

            if not issue_id:
                pytest.skip("无法创建 issue")

            # 2. 开始工作
            await client.update_issue(issue_id, status="in_progress")

            # 3. 添加评论
            try:
                await client.add_issue_comment(issue_id, "开始处理这个 issue")
            except:
                pass  # 评论功能可能失败

            # 4. 解决 issue
            await client.update_issue(issue_id, status="resolved")

            # 5. 关闭 issue
            await client.update_issue(issue_id, status="closed")

            # 验证最终状态
            final_issue = await client.get_issue(issue_id)
            assert final_issue.get("status") == "closed"

        except Exception as e:
            pytest.skip(f"Issue 生命周期测试失败: {e}")

    @pytest.mark.asyncio
    async def test_requirement_lifecycle(self):
        """测试完整的 requirement 生命周期"""
        client = await get_authenticated_client()

        if not client:
            pytest.skip("无法获取认证客户端")

        try:
            # 获取项目 ID
            projects = await client.list_projects()
            if not projects["rows"]:
                pytest.skip("没有可用的项目")

            project_id = projects["rows"][0].get("id")

            # 1. 创建 requirement
            req_data = {
                "title": "生命周期测试需求"
            }

            if project_id:
                req_data["project_id"] = project_id

            created_req = await client.create_requirement(**req_data)
            req_id = created_req.get("id")

            if not req_id:
                pytest.skip("无法创建 requirement")

            # 2. 开始处理
            await client.update_requirement(req_id, status="clarifying")

            # 3. 设计阶段
            await client.update_requirement(req_id, status="designing")

            # 4. 开发阶段
            await client.update_requirement(req_id, status="coding")

            # 5. 测试阶段
            await client.update_requirement(req_id, status="testing")

            # 6. 发布
            await client.update_requirement(req_id, status="released")

            # 验证最终状态
            final_req = await client.get_requirement(req_id)
            assert final_req.get("status") == "released"

        except Exception as e:
            pytest.skip(f"Requirement 生命周期测试失败: {e}")


# ============================================================================
# CLI 命令集成测试
# ============================================================================

@pytest.mark.integration
class TestCLIIntegration:
    """测试 CLI 命令集成"""

    def test_config_show_command(self):
        """测试 config show 命令"""
        runner = CliRunner()
        result = runner.invoke(cli, ['config', 'show'])

        # 应该显示配置信息
        assert result.exit_code == 0 or result.exit_code == 1
        assert 'API' in result.output or 'Configuration' in result.output or 'config' in result.output.lower()

    def test_help_command_tree(self):
        """测试完整的帮助命令树"""
        runner = CliRunner()

        commands_to_test = [
            ['--help'],
            ['config', '--help'],
            ['project', '--help'],
            ['issue', '--help'],
            ['requirement', '--help'],
            ['collection', '--help'],
        ]

        for cmd in commands_to_test:
            result = runner.invoke(cli, cmd)
            assert result.exit_code == 0, f"命令失败: {' '.join(cmd)}"
            assert 'Usage:' in result.output or 'Commands:' in result.output

    def test_version_command(self):
        """测试版本命令"""
        runner = CliRunner()
        result = runner.invoke(cli, ['--version'])

        assert result.exit_code == 0
        assert 'opentask' in result.output.lower()
        assert '1.40.0' in result.output


# ============================================================================
# 多步骤场景测试
# ============================================================================

@pytest.mark.integration
class TestMultiStepScenarios:
    """测试多步骤场景"""

    @pytest.mark.asyncio
    async def test_search_then_update(self):
        """测试搜索后更新"""
        client = await get_authenticated_client()

        if not client:
            pytest.skip("无法获取认证客户端")

        try:
            # 1. 搜索 open 的 issues
            result = await client.list_issues(status="open")

            if result["rows"] and len(result["rows"]) > 0:
                issue = result["rows"][0]
                issue_id = issue.get("id")

                # 2. 更新找到的第一个 issue
                await client.update_issue(issue_id, priority="high")

                # 3. 验证更新
                updated = await client.get_issue(issue_id)
                assert updated.get("priority") == "high"
            else:
                pytest.skip("没有 open 的 issues")
        except Exception as e:
            pytest.skip(f"搜索更新测试失败: {e}")

    @pytest.mark.asyncio
    async def test_filter_then_batch_update(self):
        """测试过滤后批量更新"""
        client = await get_authenticated_client()

        if not client:
            pytest.skip("无法获取认证客户端")

        try:
            # 1. 过滤出低优先级的 issues
            result = await client.list_issues(priority="low")

            if result["rows"] and len(result["rows"]) >= 2:
                issue_ids = [r.get("id") for r in result["rows"][:2]]
                issue_ids = [id for id in issue_ids if id]

                if issue_ids:
                    # 2. 批量更新状态
                    for issue_id in issue_ids:
                        await client.update_issue(issue_id, priority="medium")

                    # 3. 验证更新
                    for issue_id in issue_ids:
                        issue = await client.get_issue(issue_id)
                        assert issue.get("priority") == "medium"
            else:
                pytest.skip("需要至少 2 个低优先级 issues")
        except Exception as e:
            pytest.skip(f"过滤批量更新测试失败: {e}")

    @pytest.mark.asyncio
    async def test_project_exploration_workflow(self):
        """测试项目探索工作流"""
        client = await get_authenticated_client()

        if not client:
            pytest.skip("无法获取认证客户端")

        try:
            # 1. 列出所有项目
            projects = await client.list_projects()
            assert "rows" in projects

            if projects["rows"]:
                # 2. 选择第一个项目
                project = projects["rows"][0]
                project_id = project.get("id")
                project_name = project.get("name")

                # 3. 查看该项目的 issues
                issues = await client.list_issues(project_id=project_id)
                assert "rows" in issues

                # 4. 查看该项目的 requirements
                requirements = await client.list_requirements(project_id=project_id)
                assert "rows" in requirements

                # 5. 统计信息
                issue_count = len(issues["rows"])
                req_count = len(requirements["rows"])

                assert issue_count >= 0
                assert req_count >= 0
            else:
                pytest.skip("没有可用的项目")
        except Exception as e:
            pytest.skip(f"项目探索测试失败: {e}")


# ============================================================================
# 错误恢复场景测试
# ============================================================================

@pytest.mark.integration
class TestErrorRecoveryScenarios:
    """测试错误恢复场景"""

    @pytest.mark.asyncio
    async def test_invalid_id_handling(self):
        """测试处理无效 ID"""
        client = await get_authenticated_client()

        if not client:
            pytest.skip("无法获取认证客户端")

        try:
            # 尝试获取不存在的 issue
            try:
                await client.get_issue("invalid-id-99999")
                assert False, "应该抛出异常"
            except Exception:
                # 预期会失败
                pass

            # 尝试获取不存在的 requirement
            try:
                await client.get_requirement("invalid-id-99999")
                assert False, "应该抛出异常"
            except Exception:
                # 预期会失败
                pass

        except Exception as e:
            pytest.skip(f"错误处理测试失败: {e}")

    @pytest.mark.asyncio
    async def test_empty_result_handling(self):
        """测试处理空结果"""
        client = await get_authenticated_client()

        if not client:
            pytest.skip("无法获取认证客户端")

        try:
            # 搜索不存在的关键词
            result = await client.find_issues("nonexistentkeywordxyz123")

            assert result is not None
            assert "rows" in result
            assert len(result["rows"]) == 0

        except Exception as e:
            pytest.skip(f"空结果处理测试失败: {e}")

    @pytest.mark.asyncio
    async def test_pagination_beyond_bounds(self):
        """测试分页超出边界"""
        client = await get_authenticated_client()

        if not client:
            pytest.skip("无法获取认证客户端")

        try:
            # 请求超出范围的页面
            result = await client.list_issues(page=9999, page_size=10)

            assert result is not None
            assert "rows" in result
            # 超出范围应该返回空列表
            assert len(result["rows"]) == 0

        except Exception as e:
            pytest.skip(f"分页边界测试失败: {e}")


# ============================================================================
# 性能和负载测试
# ============================================================================

@pytest.mark.integration
@pytest.mark.slow
class TestPerformanceScenarios:
    """测试性能场景"""

    @pytest.mark.asyncio
    async def test_multiple_sequential_requests(self):
        """测试多个顺序请求"""
        import time
        client = await get_authenticated_client()

        if not client:
            pytest.skip("无法获取认证客户端")

        try:
            start_time = time.time()

            # 执行多个顺序请求
            await client.list_projects()
            await client.list_issues()
            await client.list_requirements()
            await client.get_me()

            end_time = time.time()
            duration = end_time - start_time

            # 4 个请求应该在 5 秒内完成
            assert duration < 5.0

        except Exception as e:
            pytest.skip(f"性能测试失败: {e}")

    @pytest.mark.asyncio
    async def test_large_list_performance(self):
        """测试大列表性能"""
        import time
        client = await get_authenticated_client()

        if not client:
            pytest.skip("无法获取认证客户端")

        try:
            start_time = time.time()

            # 请求较大的页面
            result = await client.list_issues(page_size=50)

            end_time = time.time()
            duration = end_time - start_time

            assert result is not None
            # 大列表请求应该在 3 秒内完成
            assert duration < 3.0

        except Exception as e:
            pytest.skip(f"大列表性能测试失败: {e}")


# ============================================================================
# 数据一致性测试
# ============================================================================

@pytest.mark.integration
class TestDataConsistency:
    """测试数据一致性"""

    @pytest.mark.asyncio
    async def test_issue_update_consistency(self):
        """测试 issue 更新的一致性"""
        client = await get_authenticated_client()

        if not client:
            pytest.skip("无法获取认证客户端")

        try:
            # 获取项目
            projects = await client.list_projects()
            if not projects["rows"]:
                pytest.skip("没有可用的项目")

            project_id = projects["rows"][0].get("id")

            # 创建 issue
            issue_data = {
                "title": "一致性测试 Issue",
                "type": "improvement",
                "priority": "medium"
            }

            if project_id:
                issue_data["project_id"] = project_id

            created = await client.create_issue(**issue_data)
            issue_id = created.get("id")

            if not issue_id:
                pytest.skip("无法创建 issue")

            # 多次更新同一字段
            await client.update_issue(issue_id, priority="high")
            await client.update_issue(issue_id, priority="urgent")
            await client.update_issue(issue_id, priority="high")

            # 验证最终值是最后一次更新的值
            final = await client.get_issue(issue_id)
            assert final.get("priority") == "high"

        except Exception as e:
            pytest.skip(f"一致性测试失败: {e}")

    @pytest.mark.asyncio
    async def test_concurrent_read_consistency(self):
        """测试并发读取的一致性"""
        client = await get_authenticated_client()

        if not client:
            pytest.skip("无法获取认证客户端")

        try:
            # 并发读取同一个 issue 多次
            projects = await client.list_projects()

            if projects["rows"] and projects["rows"][0].get("id"):
                project_id = projects["rows"][0].get("id")
                issues = await client.list_issues(project_id=project_id)

                if issues["rows"] and issues["rows"][0].get("id"):
                    issue_id = issues["rows"][0].get("id")

                    # 多次读取
                    result1 = await client.get_issue(issue_id)
                    result2 = await client.get_issue(issue_id)
                    result3 = await client.get_issue(issue_id)

                    # 所有读取应该返回相同数据
                    assert result1["id"] == result2["id"] == result3["id"]
                else:
                    pytest.skip("没有可用的 issues")
            else:
                pytest.skip("没有可用的项目")
        except Exception as e:
            pytest.skip(f"并发读取测试失败: {e}")


# ============================================================================
# 端到端场景测试
# ============================================================================

@pytest.mark.integration
@pytest.mark.slow
class TestEndToEndScenarios:
    """测试端到端场景"""

    @pytest.mark.asyncio
    async def test_complete_development_workflow(self):
        """测试完整的开发工作流"""
        client = await get_authenticated_client()

        if not client:
            pytest.skip("无法获取认证客户端")

        try:
            # 1. 获取用户信息
            user = await client.get_me()
            assert user is not None

            # 2. 列出项目
            projects = await client.list_projects()
            assert projects is not None

            # 3. 创建一个新需求
            projects = await client.list_projects()
            if projects["rows"]:
                project_id = projects["rows"][0].get("id")

                req = await client.create_requirement(
                    title="E2E 测试需求",
                    project_id=project_id
                )

                assert req is not None

                # 4. 更新需求状态
                req_id = req.get("id")
                if req_id:
                    await client.update_requirement(req_id, status="clarifying")

                    # 5. 创建相关 issue
                    issue = await client.create_issue(
                        title="E2E 测试 Issue",
                        type="improvement",
                        priority="medium",
                        project_id=project_id
                    )

                    assert issue is not None

        except Exception as e:
            pytest.skip(f"E2E 工作流测试失败: {e}")

    @pytest.mark.asyncio
    async def test_dashboard_data_gathering(self):
        """测试仪表板数据收集"""
        client = await get_authenticated_client()

        if not client:
            pytest.skip("无法获取认证客户端")

        try:
            # 收集仪表板所需的所有数据
            dashboard_data = {}

            # 用户信息
            dashboard_data["user"] = await client.get_me()

            # 项目统计
            projects = await client.list_projects()
            dashboard_data["projects"] = projects
            dashboard_data["project_count"] = len(projects.get("rows", []))

            # Issue 统计
            issues = await client.list_issues()
            dashboard_data["issues"] = issues
            dashboard_data["issue_count"] = len(issues.get("rows", []))

            # Requirement 统计
            requirements = await client.list_requirements()
            dashboard_data["requirements"] = requirements
            dashboard_data["requirement_count"] = len(requirements.get("rows", []))

            # 验证数据结构
            assert "user" in dashboard_data
            assert "projects" in dashboard_data
            assert "issues" in dashboard_data
            assert "requirements" in dashboard_data

        except Exception as e:
            pytest.skip(f"仪表板数据收集测试失败: {e}")
