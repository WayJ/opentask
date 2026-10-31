"""
Requirement API 测试

测试需求管理的完整 API 端点
"""

import pytest
from httpx import AsyncClient
from opentask.models.requirement.enums import RequirementStatus, Priority, EventType


class TestRequirementCRUD:
    """需求 CRUD 操作测试"""

    async def test_create_requirement_success(self, test_client: AsyncClient, test_token: str, test_project_id: str):
        """测试成功创建需求"""
        response = await test_client.post(
            "/api/requirements",
            headers={"Authorization": f"Bearer {test_token}"},
            json={
                "title": "自动化测试需求",
                "description": "这是一个自动化测试创建的需求",
                "priority": Priority.HIGH,
                "tags": ["测试", "自动化"],
                "project_id": test_project_id
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200
        assert data["data"]["title"] == "自动化测试需求"
        assert data["data"]["priority"] == Priority.HIGH
        assert "id" in data["data"]
        assert "code" in data["data"]  # 需求编码应该自动生成

    async def test_get_requirement_list(self, test_client: AsyncClient, test_token: str):
        """测试获取需求列表"""
        response = await test_client.get(
            "/api/requirements",
            headers={"Authorization": f"Bearer {test_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200
        assert "data" in data
        assert "total" in data["data"]

    async def test_get_requirement_detail(self, test_client: AsyncClient, test_token: str, test_project_id: str):
        """测试获取需求详情"""
        # 先创建一个需求
        create_response = await test_client.post(
            "/api/requirements",
            headers={"Authorization": f"Bearer {test_token}"},
            json={
                "title": "自动化测试需求 - 详情",
                "description": "测试获取需求详情",
                "project_id": test_project_id
            }
        )
        requirement_id = create_response.json()["data"]["id"]

        # 获取需求详情
        response = await test_client.get(
            f"/api/requirements/{requirement_id}",
            headers={"Authorization": f"Bearer {test_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200
        assert data["data"]["id"] == requirement_id

    async def test_update_requirement(self, test_client: AsyncClient, test_token: str, test_project_id: str):
        """测试更新需求"""
        # 先创建一个需求
        create_response = await test_client.post(
            "/api/requirements",
            headers={"Authorization": f"Bearer {test_token}"},
            json={
                "title": "自动化测试需求 - 更新前",
                "description": "更新前的描述",
                "project_id": test_project_id
            }
        )
        requirement_id = create_response.json()["data"]["id"]

        # 更新需求
        response = await test_client.put(
            f"/api/requirements/{requirement_id}",
            headers={"Authorization": f"Bearer {test_token}"},
            json={
                "title": "自动化测试需求 - 更新后",
                "description": "更新后的描述",
                "status": RequirementStatus.EVALUATING,
                "priority": Priority.CRITICAL
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200
        assert data["data"]["title"] == "自动化测试需求 - 更新后"
        assert data["data"]["status"] == RequirementStatus.EVALUATING

    async def test_delete_requirement(self, test_client: AsyncClient, test_token: str, test_project_id: str):
        """测试删除需求"""
        # 先创建一个需求
        create_response = await test_client.post(
            "/api/requirements",
            headers={"Authorization": f"Bearer {test_token}"},
            json={
                "title": "待删除的测试需求",
                "description": "这个需求将被删除",
                "project_id": test_project_id
            }
        )
        requirement_id = create_response.json()["data"]["id"]

        # 删除需求
        response = await test_client.delete(
            f"/api/requirements/{requirement_id}",
            headers={"Authorization": f"Bearer {test_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200

    async def test_create_requirement_missing_required_field(self, test_client: AsyncClient, test_token: str):
        """测试缺少必填字段"""
        response = await test_client.post(
            "/api/requirements",
            headers={"Authorization": f"Bearer {test_token}"},
            json={
                "description": "只有描述，没有标题"
            }
        )
        assert response.status_code == 422


class TestRequirementFilters:
    """需求过滤和搜索测试"""

    async def test_filter_by_status(self, test_client: AsyncClient, test_token: str):
        """测试按状态过滤"""
        response = await test_client.get(
            f"/api/requirements?status={RequirementStatus.PLANNING}",
            headers={"Authorization": f"Bearer {test_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200

    async def test_filter_by_priority(self, test_client: AsyncClient, test_token: str):
        """测试按优先级过滤"""
        response = await test_client.get(
            f"/api/requirements?priority={Priority.HIGH}",
            headers={"Authorization": f"Bearer {test_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200

    async def test_filter_by_project(self, test_client: AsyncClient, test_token: str, test_project_id: str):
        """测试按项目过滤"""
        response = await test_client.get(
            f"/api/requirements?project_id={test_project_id}",
            headers={"Authorization": f"Bearer {test_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200

    async def test_search_by_keyword(self, test_client: AsyncClient, test_token: str):
        """测试关键词搜索"""
        response = await test_client.get(
            "/api/requirements/search?q=自动化测试",
            headers={"Authorization": f"Bearer {test_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200
        assert isinstance(data["data"], list)

    async def test_combined_filters(self, test_client: AsyncClient, test_token: str):
        """测试组合过滤条件"""
        response = await test_client.get(
            f"/api/requirements?status={RequirementStatus.PLANNING}&priority={Priority.HIGH}",
            headers={"Authorization": f"Bearer {test_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200

    async def test_pagination(self, test_client: AsyncClient, test_token: str):
        """测试分页"""
        response = await test_client.get(
            "/api/requirements?page=1&page_size=10",
            headers={"Authorization": f"Bearer {test_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200
        assert data["data"]["page"] == 1
        assert data["data"]["page_size"] == 10


class TestRequirementAssignment:
    """需求分配测试"""

    async def test_assign_requirement(self, test_client: AsyncClient, test_token: str, test_project_id: str):
        """测试分配需求"""
        # 先创建一个需求
        create_response = await test_client.post(
            "/api/requirements",
            headers={"Authorization": f"Bearer {test_token}"},
            json={
                "title": "自动化测试需求 - 分配",
                "description": "测试需求分配功能",
                "project_id": test_project_id
            }
        )
        requirement_id = create_response.json()["data"]["id"]

        # 分配需求
        response = await test_client.post(
            f"/api/requirements/{requirement_id}/assign",
            params={"actor": "admin"},
            headers={"Authorization": f"Bearer {test_token}"},
            json={
                "assignee_id": "test-user-id"
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200
        assert data["data"]["assignee_id"] == "test-user-id"


class TestRequirementEvents:
    """需求事件测试"""

    async def test_append_event(self, test_client: AsyncClient, test_token: str, test_project_id: str):
        """测试记录事件"""
        # 先创建一个需求
        create_response = await test_client.post(
            "/api/requirements",
            headers={"Authorization": f"Bearer {test_token}"},
            json={
                "title": "自动化测试需求 - 事件",
                "description": "测试事件记录功能",
                "project_id": test_project_id
            }
        )
        requirement_id = create_response.json()["data"]["id"]

        # 记录事件：现行 API 的需求事件追加走评论端点（POST /comments, Form 字段）
        response = await test_client.post(
            f"/api/requirements/{requirement_id}/comments",
            headers={"Authorization": f"Bearer {test_token}"},
            data={"content": "这是一条测试评论"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200

    async def test_get_requirement_timeline(self, test_client: AsyncClient, test_token: str, test_project_id: str):
        """测试获取需求时间线"""
        # 先创建一个需求
        create_response = await test_client.post(
            "/api/requirements",
            headers={"Authorization": f"Bearer {test_token}"},
            json={
                "title": "自动化测试需求 - 时间线",
                "description": "测试时间线功能",
                "project_id": test_project_id
            }
        )
        requirement_id = create_response.json()["data"]["id"]

        # 获取时间线
        response = await test_client.get(
            f"/api/requirements/{requirement_id}/timeline",
            headers={"Authorization": f"Bearer {test_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200
        assert "events" in data["data"]
        assert "time_in_states" in data["data"]

class TestRequirementStatistics:
    """需求统计测试"""

    async def test_get_statistics(self, test_client: AsyncClient, test_token: str):
        """测试获取统计信息"""
        response = await test_client.get(
            "/api/requirements/statistics",
            headers={"Authorization": f"Bearer {test_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200
        assert "total" in data["data"]
        assert "by_status" in data["data"]
        assert "by_priority" in data["data"]


class TestRequirementDocuments:
    """需求文档测试"""

    async def test_get_requirement_documents(self, test_client: AsyncClient, test_token: str, test_project_id: str):
        """测试获取需求文档列表"""
        # 先创建一个需求
        create_response = await test_client.post(
            "/api/requirements",
            headers={"Authorization": f"Bearer {test_token}"},
            json={
                "title": "自动化测试需求 - 文档",
                "description": "测试文档管理功能",
                "project_id": test_project_id
            }
        )
        requirement_id = create_response.json()["data"]["id"]

        # 获取文档列表
        response = await test_client.get(
            f"/api/requirements/{requirement_id}/documents",
            headers={"Authorization": f"Bearer {test_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200
        assert "data" in data["data"]

    async def test_create_requirement_document(self, test_client: AsyncClient, test_token: str, test_project_id: str):
        """测试创建需求文档（上传文件）"""
        # 先创建一个需求
        create_response = await test_client.post(
            "/api/requirements",
            headers={"Authorization": f"Bearer {test_token}"},
            json={
                "title": "自动化测试需求 - 上传文档",
                "description": "测试文档上传功能",
                "project_id": test_project_id
            }
        )
        requirement_id = create_response.json()["data"]["id"]

        # 上传文档（使用文本文件）
        from io import BytesIO

        file_content = b"Test document content"
        files = {
            "file": ("test.txt", BytesIO(file_content), "text/plain")
        }
        data = {
            "doc_status": "DRAFT"
        }

        response = await test_client.post(
            f"/api/requirements/{requirement_id}/documents",
            headers={"Authorization": f"Bearer {test_token}"},
            files=files,
            data=data
        )
        # 上传文档端点声明 status_code=201（REST 语义：资源已创建）
        assert response.status_code == 201
        result = response.json()
        assert result["code"] == 200

    async def test_delete_requirement_document(self, test_client: AsyncClient, test_token: str, test_project_id: str):
        """测试删除需求文档"""
        # 先创建一个需求
        create_response = await test_client.post(
            "/api/requirements",
            headers={"Authorization": f"Bearer {test_token}"},
            json={
                "title": "自动化测试需求 - 删除文档",
                "description": "测试文档删除功能",
                "project_id": test_project_id
            }
        )
        requirement_id = create_response.json()["data"]["id"]

        # 先上传一个文档
        from io import BytesIO

        file_content = b"Test document to be deleted"
        files = {
            "file": ("test_delete.txt", BytesIO(file_content), "text/plain")
        }
        data = {
            "doc_status": "DRAFT"
        }

        upload_response = await test_client.post(
            f"/api/requirements/{requirement_id}/documents",
            headers={"Authorization": f"Bearer {test_token}"},
            files=files,
            data=data
        )
        document_id = upload_response.json()["data"]["id"]

        # 删除文档
        response = await test_client.delete(
            f"/api/requirements/{requirement_id}/documents/{document_id}",
            headers={"Authorization": f"Bearer {test_token}"}
        )
        assert response.status_code == 200
        result = response.json()
        assert result["code"] == 200


class TestRequirementPermissions:
    """需求权限测试"""

    async def test_unauthorized_access(self, test_client: AsyncClient):
        """测试未授权访问"""
        response = await test_client.get("/api/requirements")
        assert response.status_code == 401

    async def test_invalid_token(self, test_client: AsyncClient):
        """测试无效 token"""
        response = await test_client.get(
            "/api/requirements",
            headers={"Authorization": "Bearer invalid_token"}
        )
        assert response.status_code == 401

    async def test_get_nonexistent_requirement(self, test_client: AsyncClient, test_token: str):
        """测试获取不存在的需求"""
        response = await test_client.get(
            "/api/requirements/nonexistent-id",
            headers={"Authorization": f"Bearer {test_token}"}
        )
        assert response.status_code == 404
