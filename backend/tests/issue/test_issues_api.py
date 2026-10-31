"""
Issue 模块 API 测试

测试 Issue CRUD 操作和所有相关功能

fixtures 在 conftest_issue.py 中定义
"""

import pytest
from httpx import AsyncClient


class TestIssueCRUD:
    """Issue CRUD 操作测试"""

    @pytest.mark.asyncio
    async def test_create_issue_success(
        self, test_client: AsyncClient, test_token: str, test_project_id: str
    ):
        """测试成功创建 Issue"""
        response = await test_client.post(
            "/api/issues",
            headers={"Authorization": f"Bearer {test_token}"},
            json={
                "title": "测试 Issue - 自动化测试创建",
                "description": "这是一个自动化测试创建的 Issue",
                "type": "bug",
                "status": "open",
                "priority": "medium",
                "project_id": test_project_id,
                "reporter_id": "admin"
            }
        )

        assert response.status_code == 200
        data = response.json()["data"]

        # 验证返回的数据结构
        assert "id" in data
        assert "title" in data
        assert data["title"] == "测试 Issue - 自动化测试创建"
        assert "issue_code" in data  # 验证 issue_code 字段存在
        assert data["type"] == "bug"
        assert data["status"] == "open"
        assert data["priority"] == "medium"

    @pytest.mark.asyncio
    async def test_create_issue_missing_required_field(
        self, test_client: AsyncClient, test_token: str
    ):
        """测试缺少必填字段创建 Issue"""
        response = await test_client.post(
            "/api/issues",
            headers={"Authorization": f"Bearer {test_token}"},
            json={
                "description": "缺少标题"
            }
        )

        assert response.status_code == 422  # Validation error

    @pytest.mark.asyncio
    async def test_get_issue_list(
        self, test_client: AsyncClient, test_token: str
    ):
        """测试获取 Issue 列表"""
        response = await test_client.get(
            "/api/issues",
            headers={"Authorization": f"Bearer {test_token}"}
        )

        assert response.status_code == 200
        data = response.json()

        # 列表接口返回格式：{code, message, data: {rows, total, current, pageSize}}
        assert "data" in data
        assert "rows" in data["data"]
        assert "total" in data["data"]
        assert isinstance(data["data"]["rows"], list)

    @pytest.mark.asyncio
    async def test_get_issue_detail(
        self, test_client: AsyncClient, test_token: str, test_project_id: str
    ):
        """测试获取 Issue 详情"""
        # 先创建一个 Issue
        create_response = await test_client.post(
            "/api/issues",
            headers={"Authorization": f"Bearer {test_token}"},
            json={
                "title": "测试 Issue 详情",
                "description": "测试详情",
                "type": "feature",
                "status": "open",
                "priority": "high",
                "project_id": test_project_id,
                "reporter_id": "admin"
            }
        )

        issue_id = create_response.json()["data"]["id"]

        # 获取详情
        response = await test_client.get(
            f"/api/issues/{issue_id}",
            headers={"Authorization": f"Bearer {test_token}"}
        )

        assert response.status_code == 200
        data = response.json()["data"]

        assert data["id"] == issue_id
        assert "issue_code" in data

    @pytest.mark.asyncio
    async def test_update_issue(
        self, test_client: AsyncClient, test_token: str, test_project_id: str
    ):
        """测试更新 Issue"""
        # 创建 Issue
        create_response = await test_client.post(
            "/api/issues",
            headers={"Authorization": f"Bearer {test_token}"},
            json={
                "title": "测试 Issue 更新",
                "description": "原始描述",
                "type": "bug",
                "status": "open",
                "priority": "low",
                "project_id": test_project_id,
                "reporter_id": "admin"
            }
        )

        issue_id = create_response.json()["data"]["id"]

        # 更新 Issue
        response = await test_client.put(
            f"/api/issues/{issue_id}",
            headers={"Authorization": f"Bearer {test_token}"},
            json={
                "title": "测试 Issue 更新 - 已修改",
                "description": "更新后的描述",
                "status": "resolved",
                "priority": "critical"
            }
        )

        assert response.status_code == 200
        data = response.json()["data"]

        assert data["title"] == "测试 Issue 更新 - 已修改"
        assert data["status"] == "resolved"
        assert data["priority"] == "critical"

    @pytest.mark.asyncio
    async def test_delete_issue(
        self, test_client: AsyncClient, test_token: str, test_project_id: str
    ):
        """测试删除 Issue"""
        # 创建 Issue
        create_response = await test_client.post(
            "/api/issues",
            headers={"Authorization": f"Bearer {test_token}"},
            json={
                "title": "测试 Issue 删除",
                "description": "将被删除",
                "type": "feature",
                "status": "open",
                "priority": "low",
                "project_id": test_project_id,
                "reporter_id": "admin"
            }
        )

        issue_id = create_response.json()["data"]["id"]

        # 删除 Issue
        response = await test_client.delete(
            f"/api/issues/{issue_id}",
            headers={"Authorization": f"Bearer {test_token}"}
        )

        assert response.status_code == 200

        # 验证已删除
        get_response = await test_client.get(
            f"/api/issues/{issue_id}",
            headers={"Authorization": f"Bearer {test_token}"}
        )
        assert get_response.status_code == 404


class TestIssueFilters:
    """Issue 过滤和搜索测试"""

    @pytest.mark.asyncio
    async def test_filter_by_status(
        self, test_client: AsyncClient, test_token: str
    ):
        """测试按状态过滤"""
        response = await test_client.get(
            "/api/issues?status=open",
            headers={"Authorization": f"Bearer {test_token}"}
        )

        assert response.status_code == 200
        data = response.json()["data"]

        # 验证所有返回的 Issue 都是 todo 状态
        for issue in data["rows"]:
            assert issue["status"] == "open"

    @pytest.mark.asyncio
    async def test_filter_by_priority(
        self, test_client: AsyncClient, test_token: str
    ):
        """测试按优先级过滤"""
        response = await test_client.get(
            "/api/issues?priority=high",
            headers={"Authorization": f"Bearer {test_token}"}
        )

        assert response.status_code == 200
        data = response.json()["data"]

        for issue in data["rows"]:
            assert issue["priority"] == "high"

    @pytest.mark.asyncio
    async def test_filter_by_type(
        self, test_client: AsyncClient, test_token: str
    ):
        """测试按类型过滤"""
        response = await test_client.get(
            "/api/issues?type=bug",
            headers={"Authorization": f"Bearer {test_token}"}
        )

        assert response.status_code == 200
        data = response.json()["data"]

        for issue in data["rows"]:
            assert issue["type"] == "bug"

    @pytest.mark.asyncio
    async def test_search_by_keyword(
        self, test_client: AsyncClient, test_token: str
    ):
        """测试关键词搜索"""
        response = await test_client.get(
            "/api/issues?search=测试",
            headers={"Authorization": f"Bearer {test_token}"}
        )

        assert response.status_code == 200
        data = response.json()["data"]

        # 验证标题或描述包含关键词
        for issue in data["rows"]:
            title_has_keyword = "测试" in issue["title"]
            desc_has_keyword = "测试" in (issue.get("description") or "")
            assert title_has_keyword or desc_has_keyword

    @pytest.mark.asyncio
    async def test_combined_filters(
        self, test_client: AsyncClient, test_token: str
    ):
        """测试组合过滤"""
        response = await test_client.get(
            "/api/issues?status=open&priority=high&type=bug",
            headers={"Authorization": f"Bearer {test_token}"}
        )

        assert response.status_code == 200
        data = response.json()["data"]

        # 验证所有条件都满足
        for issue in data["rows"]:
            assert issue["status"] == "open"
            assert issue["priority"] == "high"
            assert issue["type"] == "bug"


class TestIssueComments:
    """Issue 评论功能测试"""

    @pytest.mark.asyncio
    async def test_add_comment(
        self, test_client: AsyncClient, test_token: str, test_project_id: str
    ):
        """测试添加评论"""
        # 创建 Issue
        issue_response = await test_client.post(
            "/api/issues",
            headers={"Authorization": f"Bearer {test_token}"},
            json={
                "title": "测试 Issue 评论",
                "description": "用于测试评论",
                "type": "feature",
                "status": "open",
                "project_id": test_project_id,
                "reporter_id": "admin"
            }
        )

        issue_id = issue_response.json()["data"]["id"]

        # 添加评论
        response = await test_client.post(
            f"/api/issues/{issue_id}/comments",
            headers={"Authorization": f"Bearer {test_token}"},
            json={
                "content": "这是一条测试评论"
            }
        )

        assert response.status_code == 200
        data = response.json()["data"]

        assert data["content"] == "这是一条测试评论"
        assert "user_id" in data

    @pytest.mark.asyncio
    async def test_get_comments(
        self, test_client: AsyncClient, test_token: str, test_project_id: str
    ):
        """测试获取评论列表"""
        # 创建 Issue
        issue_response = await test_client.post(
            "/api/issues",
            headers={"Authorization": f"Bearer {test_token}"},
            json={
                "title": "测试获取评论",
                "description": "测试",
                "type": "feature",
                "status": "open",
                "project_id": test_project_id,
                "reporter_id": "admin"
            }
        )

        issue_id = issue_response.json()["data"]["id"]

        # 添加两条评论
        await test_client.post(
            f"/api/issues/{issue_id}/comments",
            headers={"Authorization": f"Bearer {test_token}"},
            json={"content": "评论 1"}
        )
        await test_client.post(
            f"/api/issues/{issue_id}/comments",
            headers={"Authorization": f"Bearer {test_token}"},
            json={"content": "评论 2"}
        )

        # 获取评论列表
        response = await test_client.get(
            f"/api/issues/{issue_id}/comments",
            headers={"Authorization": f"Bearer {test_token}"}
        )

        assert response.status_code == 200
        data = response.json()["data"]

        assert len(data) == 2

    @pytest.mark.asyncio
    async def test_delete_comment(
        self, test_client: AsyncClient, test_token: str, test_project_id: str
    ):
        """测试删除评论"""
        # 创建 Issue
        issue_response = await test_client.post(
            "/api/issues",
            headers={"Authorization": f"Bearer {test_token}"},
            json={
                "title": "测试删除评论",
                "description": "测试",
                "type": "feature",
                "status": "open",
                "project_id": test_project_id,
                "reporter_id": "admin"
            }
        )

        issue_id = issue_response.json()["data"]["id"]

        # 添加评论
        comment_response = await test_client.post(
            f"/api/issues/{issue_id}/comments",
            headers={"Authorization": f"Bearer {test_token}"},
            json={"content": "将被删除的评论"}
        )

        comment_id = comment_response.json()["data"]["id"]

        # 删除评论
        response = await test_client.delete(
            f"/api/issues/comments/{comment_id}",
            headers={"Authorization": f"Bearer {test_token}"}
        )

        assert response.status_code == 200


class TestIssueCodeGeneration:
    """Issue Code 自动生成测试"""

    @pytest.mark.asyncio
    async def test_issue_code_format(
        self, test_client: AsyncClient, test_token: str, test_project_id: str
    ):
        """测试 Issue Code 格式"""
        import re
        from datetime import datetime

        # 创建多个 Issue
        created_codes = []
        for i in range(3):
            response = await test_client.post(
                "/api/issues",
                headers={"Authorization": f"Bearer {test_token}"},
                json={
                    "title": f"测试 Issue Code {i+1}",
                    "description": f"第 {i+1} 个 Issue",
                    "type": "feature",
                    "status": "open",
                    "priority": "medium",
                    "project_id": test_project_id,
                    "reporter_id": "admin"
                }
            )

            assert response.status_code == 200
            data = response.json()["data"]
            assert "issue_code" in data

            issue_code = data["issue_code"]
            created_codes.append(issue_code)

            # 验证格式：ISSUE{YEAR}-{NUMBER}
            assert re.match(r'^ISSUE\d{4}-\d+$', issue_code), f"Invalid format: {issue_code}"

            # 验证年份是当前年份
            current_year = datetime.now().year
            assert str(current_year) in issue_code, f"Year mismatch in {issue_code}"

    @pytest.mark.asyncio
    async def test_issue_code_uniqueness(
        self, test_client: AsyncClient, test_token: str, test_project_id: str
    ):
        """测试 Issue Code 唯一性"""
        created_ids = []

        # 创建多个 Issue
        for i in range(5):
            response = await test_client.post(
                "/api/issues",
                headers={"Authorization": f"Bearer {test_token}"},
                json={
                    "title": f"唯一性测试 {i+1}",
                    "description": "测试唯一性",
                    "type": "feature",
                    "status": "open",
                    "priority": "medium",
                    "project_id": test_project_id,
                    "reporter_id": "admin"
                }
            )

            assert response.status_code == 200
            issue_code = response.json()["data"]["issue_code"]
            created_ids.append(issue_code)

        # 验证所有 code 都是唯一的
        assert len(created_ids) == len(set(created_ids)), "Issue codes not unique!"

    @pytest.mark.asyncio
    async def test_issue_code_sequential_numbering(
        self, test_client: AsyncClient, test_token: str, test_project_id: str
    ):
        """测试 Issue Code 序号递增规则"""
        import re
        from datetime import datetime

        created_codes = []

        # 创建多个 Issue
        for i in range(5):
            response = await test_client.post(
                "/api/issues",
                headers={"Authorization": f"Bearer {test_token}"},
                json={
                    "title": f"序号测试 {i+1}",
                    "description": "测试序号递增",
                    "type": "feature",
                    "status": "open",
                    "priority": "medium",
                    "project_id": test_project_id,
                    "reporter_id": "admin"
                }
            )

            assert response.status_code == 200
            issue_code = response.json()["data"]["issue_code"]
            created_codes.append(issue_code)

        # 提取序号并验证递增
        current_year = datetime.now().year
        numbers = []

        for code in created_codes:
            # 提取序号部分
            match = re.match(rf'^ISSUE{current_year}-(\d+)$', code)
            assert match, f"Code format doesn't match expected pattern: {code}"
            number = int(match.group(1))
            numbers.append(number)

        # 验证序号连续递增（基于已有数量，所以不一定是1,2,3，但应该是连续的）
        sorted_numbers = sorted(numbers)
        for i in range(len(sorted_numbers) - 1):
            assert sorted_numbers[i + 1] == sorted_numbers[i] + 1, \
                f"Numbers not sequential: {sorted_numbers}"

    @pytest.mark.asyncio
    async def test_issue_code_year_isolation(
        self, test_client: AsyncClient, test_token: str, test_project_id: str
    ):
        """测试 Issue Code 年份隔离（验证 code 包含正确的年份）"""
        import re
        from datetime import datetime

        # 创建 Issue
        response = await test_client.post(
            "/api/issues",
            headers={"Authorization": f"Bearer {test_token}"},
            json={
                "title": "年份验证测试",
                "description": "验证 code 中的年份",
                "type": "feature",
                "status": "open",
                "priority": "medium",
                "project_id": test_project_id,
                "reporter_id": "admin"
            }
        )

        assert response.status_code == 200
        issue_code = response.json()["data"]["issue_code"]

        # 提取年份
        match = re.match(r'^ISSUE(\d{4})-\d+$', issue_code)
        assert match, f"Invalid code format: {issue_code}"

        code_year = int(match.group(1))
        current_year = datetime.now().year

        # 验证 code 中的年份是当前年份
        assert code_year == current_year, \
            f"Code year {code_year} doesn't match current year {current_year}"

    @pytest.mark.asyncio
    async def test_issue_code_persistence(
        self, test_client: AsyncClient, test_token: str, test_project_id: str
    ):
        """测试 Issue Code 持久化（创建后不应改变）"""
        # 创建 Issue
        create_response = await test_client.post(
            "/api/issues",
            headers={"Authorization": f"Bearer {test_token}"},
            json={
                "title": "持久化测试",
                "description": "验证 code 不会改变",
                "type": "feature",
                "status": "open",
                "priority": "medium",
                "project_id": test_project_id,
                "reporter_id": "admin"
            }
        )

        assert create_response.status_code == 200
        original_code = create_response.json()["data"]["issue_code"]
        issue_id = create_response.json()["data"]["id"]

        # 获取 Issue 详情
        get_response = await test_client.get(
            f"/api/issues/{issue_id}",
            headers={"Authorization": f"Bearer {test_token}"}
        )

        assert get_response.status_code == 200
        retrieved_code = get_response.json()["data"]["issue_code"]

        # 验证 code 没有改变
        assert original_code == retrieved_code, \
            f"Code changed from {original_code} to {retrieved_code}"

        # 更新 Issue
        update_response = await test_client.put(
            f"/api/issues/{issue_id}",
            headers={"Authorization": f"Bearer {test_token}"},
            json={
                "title": "更新后的标题",
                "status": "resolved"
            }
        )

        assert update_response.status_code == 200
        updated_code = update_response.json()["data"]["issue_code"]

        # 验证 code 仍然没有改变
        assert original_code == updated_code, \
            f"Code changed after update from {original_code} to {updated_code}"


class TestIssuePermissions:
    """Issue 权限测试"""

    @pytest.mark.asyncio
    async def test_unauthorized_access(self, test_client: AsyncClient):
        """测试未授权访问"""
        response = await test_client.get("/api/issues")
        # 缺少凭据返回 401 Unauthorized（auto_error=False 后显式抛出）
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_invalid_token(self, test_client: AsyncClient):
        """测试无效 token"""
        response = await test_client.get(
            "/api/issues",
            headers={"Authorization": "Bearer invalid_token"}
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_get_nonexistent_issue(
        self, test_client: AsyncClient, test_token: str
    ):
        """测试获取不存在的 Issue"""
        response = await test_client.get(
            "/api/issues/nonexistent-id",
            headers={"Authorization": f"Bearer {test_token}"}
        )
        assert response.status_code == 404


class TestIssueStatistics:
    """Issue 统计功能测试"""

    @pytest.mark.asyncio
    async def test_issue_statistics(
        self, test_client: AsyncClient, test_token: str
    ):
        """测试 Issue 统计"""
        response = await test_client.get(
            "/api/issues/statistics",
            headers={"Authorization": f"Bearer {test_token}"}
        )

        assert response.status_code == 200
        data = response.json()["data"]

        # 验证统计数据结构
        assert "total" in data
        assert "by_status" in data
        assert "by_priority" in data
        assert "by_type" in data


class TestIssuePagination:
    """Issue 分页测试"""

    @pytest.mark.asyncio
    async def test_pagination_default_page_size(
        self, test_client: AsyncClient, test_token: str
    ):
        """测试默认分页"""
        response = await test_client.get(
            "/api/issues",
            headers={"Authorization": f"Bearer {test_token}"}
        )

        assert response.status_code == 200
        data = response.json()["data"]

        assert "rows" in data
        assert "total" in data
        assert "current" in data
        assert "pageSize" in data

    @pytest.mark.asyncio
    async def test_pagination_custom_page_size(
        self, test_client: AsyncClient, test_token: str
    ):
        """测试自定义分页大小"""
        response = await test_client.get(
            "/api/issues?page_size=5",
            headers={"Authorization": f"Bearer {test_token}"}
        )

        assert response.status_code == 200
        data = response.json()["data"]

        # 验证返回不超过 page_size
        assert len(data["rows"]) <= 5
        assert data["pageSize"] == 5

    @pytest.mark.asyncio
    async def test_pagination_page_number(
        self, test_client: AsyncClient, test_token: str
    ):
        """测试分页页码"""
        response = await test_client.get(
            "/api/issues?page=1&page_size=10",
            headers={"Authorization": f"Bearer {test_token}"}
        )

        assert response.status_code == 200
        data = response.json()["data"]

        assert data["current"] == 1


@pytest.mark.asyncio
async def test_issue_workflow_lifecycle(
    test_client: AsyncClient, test_token: str, test_project_id: str
):
    """测试 Issue 完整生命周期"""

    # 1. 创建 Issue (todo)
    create_response = await test_client.post(
        "/api/issues",
        headers={"Authorization": f"Bearer {test_token}"},
        json={
            "title": "生命周期测试 Issue",
            "description": "测试完整的 Issue 生命周期",
            "type": "bug",
            "status": "open",
            "priority": "medium",
            "project_id": test_project_id,
            "reporter_id": "admin"
        }
    )
    assert create_response.status_code == 200
    issue_id = create_response.json()["data"]["id"]
    issue_code = create_response.json()["data"]["issue_code"]

    # 2. 更新为进行中
    update_response = await test_client.put(
        f"/api/issues/{issue_id}",
        headers={"Authorization": f"Bearer {test_token}"},
        json={"status": "in_progress"}
    )
    assert update_response.status_code == 200
    assert update_response.json()["data"]["status"] == "in_progress"

    # 3. 添加评论
    comment_response = await test_client.post(
        f"/api/issues/{issue_id}/comments",
        headers={"Authorization": f"Bearer {test_token}"},
        json={"content": "处理中..."}
    )
    assert comment_response.status_code == 200

    # 4. 更新为等待反馈
    update_response = await test_client.put(
        f"/api/issues/{issue_id}",
        headers={"Authorization": f"Bearer {test_token}"},
        json={"status": "feedback"}
    )
    assert update_response.status_code == 200

    # 5. 更新为已解决
    update_response = await test_client.put(
        f"/api/issues/{issue_id}",
        headers={"Authorization": f"Bearer {test_token}"},
        json={"status": "resolved"}
    )
    assert update_response.status_code == 200

    # 6. 完成Issue
    update_response = await test_client.put(
        f"/api/issues/{issue_id}",
        headers={"Authorization": f"Bearer {test_token}"},
        json={"status": "closed"}
    )
    assert update_response.status_code == 200
    assert update_response.json()["data"]["status"] == "closed"

    # 7. 验证历史记录
    timeline_response = await test_client.get(
        f"/api/issues/{issue_id}/timeline",
        headers={"Authorization": f"Bearer {test_token}"}
    )
    assert timeline_response.status_code == 200
    timeline = timeline_response.json()["data"]

    # 验证历史记录包含状态变更（时间线接口返回 data={rows,total}）
    timeline_rows = timeline["rows"]
    status_changes = [t for t in timeline_rows if t["action_type"] == "status_changed"]
    assert len(status_changes) >= 4  # open -> in_progress -> feedback -> resolved -> closed
