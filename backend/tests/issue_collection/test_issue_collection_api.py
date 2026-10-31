"""
Issue Collection API 单元测试
"""
import pytest
import pytest_asyncio
from httpx import AsyncClient


class TestIssueCollectionAPI:
    """问题集 API 测试类"""

    @pytest.mark.asyncio
    async def test_create_collection(self, test_client: AsyncClient, test_token: str):
        """测试创建问题集"""
        response = await test_client.post(
            "/api/issues/collections",
            headers={"Authorization": f"Bearer {test_token}"},
            json={
                "title": "自动化测试 - 问题集",
                "description": "这是一个自动化测试的问题集描述",
                "status": "pending"
            }
        )

        assert response.status_code == 200, f"创建失败: {response.text}"
        data = response.json()["data"]

        assert data["title"] == "自动化测试 - 问题集"
        assert data["description"] == "这是一个自动化测试的问题集描述"
        assert data["status"] == "pending"
        assert "id" in data
        assert "created_at" in data

    @pytest.mark.asyncio
    async def test_get_collections(self, test_client: AsyncClient, test_token: str):
        """测试获取问题集列表"""
        # 先创建一个测试问题集
        create_response = await test_client.post(
            "/api/issues/collections",
            headers={"Authorization": f"Bearer {test_token}"},
            json={
                "title": "自动化测试 - 列表测试",
                "description": "用于测试列表功能",
                "status": "pending"
            }
        )
        assert create_response.status_code == 200

        # 获取列表
        response = await test_client.get(
            "/api/issues/collections?page=1&page_size=10",
            headers={"Authorization": f"Bearer {test_token}"}
        )

        assert response.status_code == 200
        data = response.json()["data"]

        assert "rows" in data
        assert "total" in data
        assert isinstance(data["rows"], list)

    @pytest.mark.asyncio
    async def test_get_collection_detail(self, test_client: AsyncClient, test_token: str):
        """测试获取问题集详情"""
        # 创建问题集
        create_response = await test_client.post(
            "/api/issues/collections",
            headers={"Authorization": f"Bearer {test_token}"},
            json={
                "title": "自动化测试 - 详情测试",
                "description": "用于测试详情功能",
                "status": "pending"
            }
        )
        assert create_response.status_code == 200
        collection_id = create_response.json()["data"]["id"]

        # 获取详情
        response = await test_client.get(
            f"/api/issues/collections/{collection_id}",
            headers={"Authorization": f"Bearer {test_token}"}
        )

        assert response.status_code == 200
        data = response.json()["data"]

        assert data["id"] == collection_id
        assert data["title"] == "自动化测试 - 详情测试"

    @pytest.mark.asyncio
    async def test_update_collection(self, test_client: AsyncClient, test_token: str):
        """测试更新问题集"""
        # 创建问题集
        create_response = await test_client.post(
            "/api/issues/collections",
            headers={"Authorization": f"Bearer {test_token}"},
            json={
                "title": "自动化测试 - 更新前",
                "description": "原始描述",
                "status": "pending"
            }
        )
        assert create_response.status_code == 200
        collection_id = create_response.json()["data"]["id"]

        # 更新问题集
        update_response = await test_client.put(
            f"/api/issues/collections/{collection_id}",
            headers={"Authorization": f"Bearer {test_token}"},
            json={
                "title": "自动化测试 - 更新后",
                "description": "更新后的描述",
                "status": "in_progress"
            }
        )

        assert update_response.status_code == 200
        data = update_response.json()["data"]

        assert data["title"] == "自动化测试 - 更新后"
        assert data["description"] == "更新后的描述"
        assert data["status"] == "in_progress"

    @pytest.mark.asyncio
    async def test_delete_collection(self, test_client: AsyncClient, test_token: str):
        """测试删除问题集"""
        # 创建问题集
        create_response = await test_client.post(
            "/api/issues/collections",
            headers={"Authorization": f"Bearer {test_token}"},
            json={
                "title": "自动化测试 - 删除测试",
                "description": "用于测试删除功能",
                "status": "pending"
            }
        )
        assert create_response.status_code == 200
        collection_id = create_response.json()["data"]["id"]

        # 删除问题集
        delete_response = await test_client.delete(
            f"/api/issues/collections/{collection_id}",
            headers={"Authorization": f"Bearer {test_token}"}
        )

        assert delete_response.status_code == 200

        # 验证删除成功
        get_response = await test_client.get(
            f"/api/issues/collections/{collection_id}",
            headers={"Authorization": f"Bearer {test_token}"}
        )
        assert get_response.status_code == 404

    @pytest.mark.asyncio
    async def test_parse_collection(self, test_client: AsyncClient, test_token: str):
        """测试拆解问题集 API"""
        # 创建问题集
        create_response = await test_client.post(
            "/api/issues/collections",
            headers={"Authorization": f"Bearer {test_token}"},
            json={
                "title": "自动化测试 - 拆解测试",
                "description": "用于测试拆解功能",
                "status": "pending"
            }
        )
        assert create_response.status_code == 200
        collection_id = create_response.json()["data"]["id"]

        # 调用拆解 API
        parse_response = await test_client.post(
            f"/api/issues/collections/{collection_id}/parse",
            headers={"Authorization": f"Bearer {test_token}"},
            json={
                "issues": [
                    {
                        "title": "自动化测试 - Issue 1",
                        "description": "这是第一个测试 Issue",
                        "type": "bug",
                        "priority": "high"
                    },
                    {
                        "title": "自动化测试 - Issue 2",
                        "description": "这是第二个测试 Issue",
                        "type": "feature",
                        "priority": "medium"
                    }
                ]
            }
        )

        assert parse_response.status_code == 200
        data = parse_response.json()["data"]

        assert "parsed_count" in data
        assert data["parsed_count"] == 2
        assert "issue_ids" in data
        assert len(data["issue_ids"]) == 2

    @pytest.mark.asyncio
    async def test_get_statistics(self, test_client: AsyncClient, test_token: str):
        """测试获取统计信息"""
        # 创建问题集
        create_response = await test_client.post(
            "/api/issues/collections",
            headers={"Authorization": f"Bearer {test_token}"},
            json={
                "title": "自动化测试 - 统计测试",
                "description": "用于测试统计功能",
                "status": "pending"
            }
        )
        assert create_response.status_code == 200
        collection_id = create_response.json()["data"]["id"]

        # 获取统计信息
        response = await test_client.get(
            f"/api/issues/collections/{collection_id}/statistics",
            headers={"Authorization": f"Bearer {test_token}"}
        )

        assert response.status_code == 200
        data = response.json()["data"]

        assert "total" in data
        assert "completed" in data
        assert "in_progress" in data
        assert "pending" in data
        assert "completion_rate" in data

    @pytest.mark.asyncio
    async def test_collection_filter_by_status(self, test_client: AsyncClient, test_token: str):
        """测试按状态筛选问题集"""
        # 创建不同状态的问题集
        for status in ["pending", "in_progress", "completed"]:
            await test_client.post(
                "/api/issues/collections",
                headers={"Authorization": f"Bearer {test_token}"},
                json={
                    "title": f"自动化测试 - {status} 状态",
                    "description": f"状态为 {status} 的测试问题集",
                    "status": status
                }
            )

        # 按状态筛选
        response = await test_client.get(
            "/api/issues/collections?status=pending&page=1&page_size=10",
            headers={"Authorization": f"Bearer {test_token}"}
        )

        assert response.status_code == 200
        data = response.json()["data"]
        rows = data["rows"]

        # 验证返回的都是 pending 状态
        for row in rows:
            assert row["status"] == "pending"

    @pytest.mark.asyncio
    async def test_collection_search(self, test_client: AsyncClient, test_token: str):
        """测试搜索功能"""
        # 创建问题集
        await test_client.post(
            "/api/issues/collections",
            headers={"Authorization": f"Bearer {test_token}"},
            json={
                "title": "自动化测试 - 搜索测试 UNIQUE_KEYWORD_123",
                "description": "用于测试搜索功能",
                "status": "pending"
            }
        )

        # 搜索
        response = await test_client.get(
            "/api/issues/collections?search=UNIQUE_KEYWORD_123&page=1&page_size=10",
            headers={"Authorization": f"Bearer {test_token}"}
        )

        assert response.status_code == 200
        rows = response.json()["data"]["rows"]
        assert len(rows) > 0
        assert "UNIQUE_KEYWORD_123" in rows[0]["title"]

    @pytest.mark.asyncio
    async def test_unauthorized_access(self, test_client: AsyncClient):
        """测试未授权访问"""
        # 不带 token 的请求
        response = await test_client.get("/api/issues/collections")

        # 401 (Unauthorized) 或 403 (Forbidden) 都是可以接受的
        assert response.status_code in [401, 403], f"Expected 401 or 403, got {response.status_code}"

    @pytest.mark.asyncio
    async def test_invalid_collection_id(self, test_client: AsyncClient, test_token: str):
        """测试无效的问题集 ID"""
        fake_id = "non-existent-id-12345"

        response = await test_client.get(
            f"/api/issues/collections/{fake_id}",
            headers={"Authorization": f"Bearer {test_token}"}
        )

        assert response.status_code == 404
