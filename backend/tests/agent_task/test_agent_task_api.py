"""
Agent Task API 测试

测试任务分发管理的完整 API 端点
"""

import pytest
from httpx import AsyncClient


class TestAgentTaskCRUD:
    """Agent Task CRUD 操作测试"""

    async def test_create_task_success(self, test_client: AsyncClient, test_token: str):
        """测试成功创建任务"""
        response = await test_client.post(
            "/api/tasks",
            headers={"Authorization": f"Bearer {test_token}"},
            json={
                "title": "自动化测试任务",
                "description": "这是一个自动化测试创建的任务",
                "priority": "HIGH",
                "assignee": "agent-001",
                "deadline": "2025-12-31T23:59:59Z",
                "metadata": {"test": True},
                "requirements": ["REQ-001"]
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200
        assert data["data"]["title"] == "自动化测试任务"
        assert data["data"]["priority"] == "HIGH"
        assert data["data"]["assignee"] == "agent-001"
        assert "task_id" in data["data"]

    async def test_create_task_minimal(self, test_client: AsyncClient, test_token: str):
        """测试创建最小任务（只填必填字段）"""
        response = await test_client.post(
            "/api/tasks",
            headers={"Authorization": f"Bearer {test_token}"},
            json={
                "title": "最小测试任务",
                "description": "只包含必填字段",
                "priority": "MEDIUM",
                "assignee": "agent-002"
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200
        assert data["data"]["title"] == "最小测试任务"

    async def test_get_task_list(self, test_client: AsyncClient, test_token: str):
        """测试获取任务列表"""
        response = await test_client.get(
            "/api/tasks",
            headers={"Authorization": f"Bearer {test_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200
        assert "data" in data
        assert "rows" in data["data"]
        assert "total" in data["data"]

    async def test_get_task_detail(self, test_client: AsyncClient, test_token: str):
        """测试获取任务详情"""
        # 先创建一个任务
        create_response = await test_client.post(
            "/api/tasks",
            headers={"Authorization": f"Bearer {test_token}"},
            json={
                "title": "自动化测试任务 - 详情",
                "description": "测试获取任务详情",
                "priority": "MEDIUM",
                "assignee": "agent-001"
            }
        )
        task_id = create_response.json()["data"]["task_id"]

        # 获取任务详情
        response = await test_client.get(
            f"/api/tasks/{task_id}",
            headers={"Authorization": f"Bearer {test_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200
        assert data["data"]["task_id"] == task_id

    async def test_update_task_status(self, test_client: AsyncClient, test_token: str):
        """测试更新任务状态"""
        # 先创建一个任务
        create_response = await test_client.post(
            "/api/tasks",
            headers={"Authorization": f"Bearer {test_token}"},
            json={
                "title": "自动化测试任务 - 更新",
                "description": "测试更新任务状态",
                "priority": "MEDIUM",
                "assignee": "agent-001"
            }
        )
        task_id = create_response.json()["data"]["task_id"]

        # 更新任务状态
        response = await test_client.patch(
            f"/api/tasks/{task_id}",
            headers={"Authorization": f"Bearer {test_token}"},
            json={
                "status": "RUNNING",
                "progress_percentage": 50,
                "current_step": "执行中",
                "logs": [
                    {
                        "level": "INFO",
                        "message": "任务开始执行",
                        "timestamp": "2025-03-15T12:00:00Z"
                    }
                ]
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200
        assert data["data"]["status"] == "RUNNING"
        assert data["data"]["progress_percentage"] == 50

    async def test_cancel_task(self, test_client: AsyncClient, test_token: str):
        """测试取消任务"""
        # 先创建一个任务
        create_response = await test_client.post(
            "/api/tasks",
            headers={"Authorization": f"Bearer {test_token}"},
            json={
                "title": "待取消的测试任务",
                "description": "这个任务将被取消",
                "priority": "LOW",
                "assignee": "agent-003"
            }
        )
        task_id = create_response.json()["data"]["task_id"]

        # 取消任务
        response = await test_client.post(
            f"/api/tasks/{task_id}/cancel",
            headers={"Authorization": f"Bearer {test_token}"},
            json={"reason": "测试取消"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200
        assert data["data"]["status"] == "CANCELLED"

    async def test_delete_task(self, test_client: AsyncClient, test_token: str):
        """测试删除任务"""
        # 先创建一个任务
        create_response = await test_client.post(
            "/api/tasks",
            headers={"Authorization": f"Bearer {test_token}"},
            json={
                "title": "待删除的测试任务",
                "description": "这个任务将被删除",
                "priority": "LOW",
                "assignee": "agent-003"
            }
        )
        task_id = create_response.json()["data"]["task_id"]

        # 删除任务
        response = await test_client.delete(
            f"/api/tasks/{task_id}",
            headers={"Authorization": f"Bearer {test_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200

    async def test_create_task_missing_required_field(self, test_client: AsyncClient, test_token: str):
        """测试缺少必填字段"""
        response = await test_client.post(
            "/api/tasks",
            headers={"Authorization": f"Bearer {test_token}"},
            json={
                "description": "只有描述，没有标题"
            }
        )
        assert response.status_code == 422  # Validation error

    async def test_create_task_invalid_priority(self, test_client: AsyncClient, test_token: str):
        """测试无效的优先级"""
        response = await test_client.post(
            "/api/tasks",
            headers={"Authorization": f"Bearer {test_token}"},
            json={
                "title": "测试任务",
                "description": "测试无效优先级",
                "priority": "INVALID_PRIORITY",
                "assignee": "agent-001"
            }
        )
        assert response.status_code == 400  # Bad Request


class TestAgentTaskFilters:
    """Agent Task 过滤和搜索测试"""

    async def test_filter_by_status(self, test_client: AsyncClient, test_token: str):
        """测试按状态过滤"""
        response = await test_client.get(
            "/api/tasks?status=PENDING",
            headers={"Authorization": f"Bearer {test_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200

    async def test_filter_by_assignee(self, test_client: AsyncClient, test_token: str):
        """测试按分配对象过滤"""
        response = await test_client.get(
            "/api/tasks?assignee=agent-001",
            headers={"Authorization": f"Bearer {test_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200

    async def test_pagination(self, test_client: AsyncClient, test_token: str):
        """测试分页"""
        response = await test_client.get(
            "/api/tasks?limit=10&offset=0",
            headers={"Authorization": f"Bearer {test_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200
        assert data["data"]["pageSize"] == 10

    async def test_combined_filters(self, test_client: AsyncClient, test_token: str):
        """测试组合过滤条件"""
        response = await test_client.get(
            "/api/tasks?status=PENDING&assignee=agent-001&limit=5",
            headers={"Authorization": f"Bearer {test_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200


class TestAgentTaskStatistics:
    """Agent Task 统计测试"""

    async def test_get_statistics(self, test_client: AsyncClient, test_token: str):
        """测试获取统计信息"""
        response = await test_client.get(
            "/api/tasks/stats/summary",
            headers={"Authorization": f"Bearer {test_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200
        assert "total" in data["data"]
        assert "by_status" in data["data"]
        assert "by_priority" in data["data"]


class TestAgentTaskPermissions:
    """Agent Task 权限测试"""

    async def test_unauthorized_access(self, test_client: AsyncClient):
        """测试未授权访问"""
        response = await test_client.get("/api/tasks")
        assert response.status_code == 401  # Unauthorized

    async def test_invalid_token(self, test_client: AsyncClient):
        """测试无效 token"""
        response = await test_client.get(
            "/api/tasks",
            headers={"Authorization": "Bearer invalid_token"}
        )
        assert response.status_code == 401  # Unauthorized

    async def test_get_nonexistent_task(self, test_client: AsyncClient, test_token: str):
        """测试获取不存在的任务"""
        response = await test_client.get(
            "/api/tasks/nonexistent-task-id",
            headers={"Authorization": f"Bearer {test_token}"}
        )
        assert response.status_code == 404  # Not Found

    async def test_update_nonexistent_task(self, test_client: AsyncClient, test_token: str):
        """测试更新不存在的任务"""
        response = await test_client.patch(
            "/api/tasks/nonexistent-task-id",
            headers={"Authorization": f"Bearer {test_token}"},
            json={"status": "RUNNING"}
        )
        assert response.status_code == 404  # Not Found

    async def test_delete_nonexistent_task(self, test_client: AsyncClient, test_token: str):
        """测试删除不存在的任务"""
        response = await test_client.delete(
            "/api/tasks/nonexistent-task-id",
            headers={"Authorization": f"Bearer {test_token}"}
        )
        assert response.status_code == 404  # Not Found


class TestAgentTaskEdgeCases:
    """Agent Task 边界情况测试"""

    async def test_update_with_invalid_status(self, test_client: AsyncClient, test_token: str):
        """测试使用无效状态更新任务"""
        # 先创建一个任务
        create_response = await test_client.post(
            "/api/tasks",
            headers={"Authorization": f"Bearer {test_token}"},
            json={
                "title": "测试无效状态",
                "description": "测试边界情况",
                "priority": "MEDIUM",
                "assignee": "agent-001"
            }
        )
        task_id = create_response.json()["data"]["task_id"]

        # 尝试用无效状态更新
        response = await test_client.patch(
            f"/api/tasks/{task_id}",
            headers={"Authorization": f"Bearer {test_token}"},
            json={"status": "INVALID_STATUS"}
        )
        assert response.status_code == 400  # Bad Request

    async def test_progress_percentage_boundary(self, test_client: AsyncClient, test_token: str):
        """测试进度百分比边界值"""
        # 先创建一个任务
        create_response = await test_client.post(
            "/api/tasks",
            headers={"Authorization": f"Bearer {test_token}"},
            json={
                "title": "测试进度边界",
                "description": "测试 0% 和 100%",
                "priority": "MEDIUM",
                "assignee": "agent-001"
            }
        )
        task_id = create_response.json()["data"]["task_id"]

        # 测试 0%
        response = await test_client.patch(
            f"/api/tasks/{task_id}",
            headers={"Authorization": f"Bearer {test_token}"},
            json={"progress_percentage": 0}
        )
        assert response.status_code == 200

        # 测试 100%
        response = await test_client.patch(
            f"/api/tasks/{task_id}",
            headers={"Authorization": f"Bearer {test_token}"},
            json={"progress_percentage": 100}
        )
        assert response.status_code == 200

    async def test_task_with_metadata(self, test_client: AsyncClient, test_token: str):
        """测试带元数据的任务"""
        metadata = {
            "project": "测试项目",
            "sprint": "Sprint 1",
            "labels": ["bug", "urgent"],
            "complexity": 8
        }

        response = await test_client.post(
            "/api/tasks",
            headers={"Authorization": f"Bearer {test_token}"},
            json={
                "title": "测试元数据",
                "description": "测试自定义元数据字段",
                "priority": "HIGH",
                "assignee": "agent-001",
                "metadata": metadata
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200
        assert data["data"]["metadata"] == metadata

    async def test_task_with_requirements(self, test_client: AsyncClient, test_token: str):
        """测试关联需求的任务"""
        requirements = ["REQ-001", "REQ-002", "REQ-003"]

        response = await test_client.post(
            "/api/tasks",
            headers={"Authorization": f"Bearer {test_token}"},
            json={
                "title": "测试需求关联",
                "description": "测试关联多个需求",
                "priority": "MEDIUM",
                "assignee": "agent-001",
                "requirements": requirements
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200
        assert data["data"]["requirements"] == requirements
