"""
知识库模块 API 测试

测试知识库 CRUD 操作和所有相关功能
"""

import pytest
from httpx import AsyncClient


class TestKnowledgeBaseCRUD:
    """知识库 CRUD 操作测试"""

    @pytest.mark.asyncio
    async def test_create_knowledge_base_success(
        self, test_client: AsyncClient, test_token: str
    ):
        """测试成功创建知识库"""
        response = await test_client.post(
            "/knowledge-bases",
            headers={"Authorization": f"Bearer {test_token}"},
            json={
                "name": "新知识库",
                "description": "这是一个新知识库",
                "icon": "📖"
            }
        )

        assert response.status_code == 200
        data = response.json()["data"]

        assert "id" in data
        assert "name" in data
        assert data["name"] == "新知识库"
        assert data["description"] == "这是一个新知识库"
        assert data["icon"] == "📖"
        assert data["status"] == "active"

        # 清理
        await test_client.delete(
            f"/knowledge-bases/{data['id']}",
            headers={"Authorization": f"Bearer {test_token}"}
        )

    @pytest.mark.asyncio
    async def test_create_knowledge_base_missing_name(
        self, test_client: AsyncClient, test_token: str
    ):
        """测试缺少必填字段创建知识库"""
        response = await test_client.post(
            "/knowledge-bases",
            headers={"Authorization": f"Bearer {test_token}"},
            json={
                "description": "缺少名称"
            }
        )

        assert response.status_code == 422  # Validation error

    @pytest.mark.asyncio
    async def test_get_knowledge_base_list(
        self, test_client: AsyncClient, test_token: str
    ):
        """测试获取知识库列表"""
        response = await test_client.get(
            "/knowledge-bases",
            headers={"Authorization": f"Bearer {test_token}"}
        )

        assert response.status_code == 200
        data = response.json()

        assert "data" in data
        assert "rows" in data["data"]
        assert "total" in data["data"]
        assert isinstance(data["data"]["rows"], list)

    @pytest.mark.asyncio
    async def test_get_knowledge_base_detail(
        self, test_client: AsyncClient, test_token: str, test_kb_id: str
    ):
        """测试获取知识库详情"""
        response = await test_client.get(
            f"/knowledge-bases/{test_kb_id}",
            headers={"Authorization": f"Bearer {test_token}"}
        )

        assert response.status_code == 200
        data = response.json()["data"]

        assert data["id"] == test_kb_id
        assert "name" in data
        assert "file_path" in data

    @pytest.mark.asyncio
    async def test_update_knowledge_base(
        self, test_client: AsyncClient, test_token: str, test_kb_id: str
    ):
        """测试更新知识库"""
        response = await test_client.put(
            f"/knowledge-bases/{test_kb_id}",
            headers={"Authorization": f"Bearer {test_token}"},
            json={
                "name": "更新的知识库名称",
                "description": "更新的描述",
                "icon": "🎯"
            }
        )

        assert response.status_code == 200
        data = response.json()["data"]

        assert data["name"] == "更新的知识库名称"
        assert data["description"] == "更新的描述"
        assert data["icon"] == "🎯"

    @pytest.mark.asyncio
    async def test_delete_knowledge_base(
        self, test_client: AsyncClient, test_token: str
    ):
        """测试删除知识库"""
        # 先创建一个知识库
        create_response = await test_client.post(
            "/knowledge-bases",
            headers={"Authorization": f"Bearer {test_token}"},
            json={
                "name": "将被删除的知识库",
                "description": "测试删除"
            }
        )

        kb_id = create_response.json()["data"]["id"]

        # 删除知识库
        response = await test_client.delete(
            f"/knowledge-bases/{kb_id}",
            headers={"Authorization": f"Bearer {test_token}"}
        )

        assert response.status_code == 200

        # 验证已删除
        get_response = await test_client.get(
            f"/knowledge-bases/{kb_id}",
            headers={"Authorization": f"Bearer {test_token}"}
        )
        assert get_response.status_code == 404


class TestKnowledgeCRUD:
    """知识文档 CRUD 操作测试"""

    @pytest.mark.asyncio
    async def test_create_knowledge_success(
        self, test_client: AsyncClient, test_token: str, test_kb_id: str
    ):
        """测试成功创建知识文档"""
        response = await test_client.post(
            "/knowledge",
            headers={"Authorization": f"Bearer {test_token}"},
            json={
                "title": "测试文档",
                "content": "# 测试文档\n\n这是文档内容",
                "knowledgeBaseId": test_kb_id,
                "status": "draft"
            }
        )

        assert response.status_code == 200
        data = response.json()["data"]

        assert "id" in data
        assert "title" in data
        assert data["title"] == "测试文档"
        assert data["status"] == "draft"
        assert "slug" in data
        assert "version" in data

        # 清理
        await test_client.delete(
            f"/knowledge/{data['id']}",
            headers={"Authorization": f"Bearer {test_token}"}
        )

    @pytest.mark.asyncio
    async def test_create_knowledge_missing_title(
        self, test_client: AsyncClient, test_token: str, test_kb_id: str
    ):
        """测试缺少标题创建文档"""
        response = await test_client.post(
            "/knowledge",
            headers={"Authorization": f"Bearer {test_token}"},
            json={
                "content": "缺少标题",
                "knowledgeBaseId": test_kb_id
            }
        )

        assert response.status_code == 422  # Validation error

    @pytest.mark.asyncio
    async def test_get_knowledge_list(
        self, test_client: AsyncClient, test_token: str
    ):
        """测试获取知识文档列表"""
        response = await test_client.get(
            "/knowledge",
            headers={"Authorization": f"Bearer {test_token}"}
        )

        assert response.status_code == 200
        data = response.json()

        assert "data" in data
        assert "rows" in data["data"]
        assert "total" in data["data"]
        assert isinstance(data["data"]["rows"], list)

    @pytest.mark.asyncio
    async def test_get_knowledge_detail(
        self, test_client: AsyncClient, test_token: str, test_knowledge_id: str
    ):
        """测试获取知识文档详情"""
        response = await test_client.get(
            f"/knowledge/{test_knowledge_id}",
            headers={"Authorization": f"Bearer {test_token}"}
        )

        assert response.status_code == 200
        data = response.json()["data"]

        assert data["id"] == test_knowledge_id
        assert "title" in data
        assert "content" in data
        assert "file_path" in data

    @pytest.mark.asyncio
    async def test_update_knowledge(
        self, test_client: AsyncClient, test_token: str, test_knowledge_id: str
    ):
        """测试更新知识文档"""
        response = await test_client.put(
            f"/knowledge/{test_knowledge_id}",
            headers={"Authorization": f"Bearer {test_token}"},
            json={
                "title": "更新的标题",
                "content": "# 更新的内容\n\n这是更新后的文档",
                "status": "published"
            }
        )

        assert response.status_code == 200
        data = response.json()["data"]

        assert data["title"] == "更新的标题"
        assert "更新后的内容" in data["content"]
        assert data["status"] == "published"

    @pytest.mark.asyncio
    async def test_delete_knowledge(
        self, test_client: AsyncClient, test_token: str, test_kb_id: str
    ):
        """测试删除知识文档"""
        # 先创建一个文档
        create_response = await test_client.post(
            "/knowledge",
            headers={"Authorization": f"Bearer {test_token}"},
            json={
                "title": "将被删除的文档",
                "content": "测试删除",
                "knowledgeBaseId": test_kb_id
            }
        )

        knowledge_id = create_response.json()["data"]["id"]

        # 删除文档
        response = await test_client.delete(
            f"/knowledge/{knowledge_id}",
            headers={"Authorization": f"Bearer {test_token}"}
        )

        assert response.status_code == 200

        # 验证已删除
        get_response = await test_client.get(
            f"/knowledge/{knowledge_id}",
            headers={"Authorization": f"Bearer {test_token}"}
        )
        assert get_response.status_code == 404


class TestKnowledgeFilters:
    """知识文档过滤和搜索测试"""

    @pytest.mark.asyncio
    async def test_filter_by_status(
        self, test_client: AsyncClient, test_token: str
    ):
        """测试按状态过滤"""
        response = await test_client.get(
            "/knowledge?status=draft",
            headers={"Authorization": f"Bearer {test_token}"}
        )

        assert response.status_code == 200
        data = response.json()["data"]

        for knowledge in data["rows"]:
            assert knowledge["status"] == "draft"

    @pytest.mark.asyncio
    async def test_filter_by_knowledge_base(
        self, test_client: AsyncClient, test_token: str, test_kb_id: str
    ):
        """测试按知识库过滤"""
        response = await test_client.get(
            f"/knowledge?knowledgeBaseId={test_kb_id}",
            headers={"Authorization": f"Bearer {test_token}"}
        )

        assert response.status_code == 200
        data = response.json()["data"]

        for knowledge in data["rows"]:
            assert knowledge["knowledgeBaseId"] == test_kb_id

    @pytest.mark.asyncio
    async def test_search_by_keyword(
        self, test_client: AsyncClient, test_token: str
    ):
        """测试关键词搜索"""
        response = await test_client.get(
            "/knowledge?search=测试",
            headers={"Authorization": f"Bearer {test_token}"}
        )

        assert response.status_code == 200
        data = response.json()["data"]

        # 验证标题或内容包含关键词
        for knowledge in data["rows"]:
            title_has_keyword = "测试" in knowledge["title"]
            content_has_keyword = "测试" in (knowledge.get("content") or "")
            assert title_has_keyword or content_has_keyword


class TestKnowledgePublishing:
    """知识文档发布功能测试"""

    @pytest.mark.asyncio
    async def test_publish_knowledge(
        self, test_client: AsyncClient, test_token: str, test_knowledge_id: str
    ):
        """测试发布知识文档"""
        response = await test_client.post(
            f"/knowledge/{test_knowledge_id}/publish",
            headers={"Authorization": f"Bearer {test_token}"}
        )

        assert response.status_code == 200
        data = response.json()["data"]

        assert data["status"] == "published"

    @pytest.mark.asyncio
    async def test_unpublish_knowledge(
        self, test_client: AsyncClient, test_token: str, test_kb_id: str
    ):
        """测试取消发布知识文档"""
        # 先创建一个已发布的文档
        create_response = await test_client.post(
            "/knowledge",
            headers={"Authorization": f"Bearer {test_token}"},
            json={
                "title": "发布测试",
                "content": "测试内容",
                "knowledgeBaseId": test_kb_id,
                "status": "published"
            }
        )

        knowledge_id = create_response.json()["data"]["id"]

        # 取消发布
        response = await test_client.post(
            f"/knowledge/{knowledge_id}/unpublish",
            headers={"Authorization": f"Bearer {test_token}"}
        )

        assert response.status_code == 200
        data = response.json()["data"]

        assert data["status"] == "draft"

        # 清理
        await test_client.delete(
            f"/knowledge/{knowledge_id}",
            headers={"Authorization": f"Bearer {test_token}"}
        )


class TestKnowledgeVersioning:
    """知识文档版本控制测试"""

    @pytest.mark.asyncio
    async def test_version_increment_on_update(
        self, test_client: AsyncClient, test_token: str, test_knowledge_id: str
    ):
        """测试更新时版本号递增"""
        # 获取初始版本
        get_response = await test_client.get(
            f"/knowledge/{test_knowledge_id}",
            headers={"Authorization": f"Bearer {test_token}"}
        )
        initial_version = get_response.json()["data"]["version"]

        # 更新文档
        await test_client.put(
            f"/knowledge/{test_knowledge_id}",
            headers={"Authorization": f"Bearer {test_token}"},
            json={
                "title": "更新版本测试",
                "content": "新内容"
            }
        )

        # 获取更新后的版本
        get_response = await test_client.get(
            f"/knowledge/{test_knowledge_id}",
            headers={"Authorization": f"Bearer {test_token}"}
        )
        new_version = get_response.json()["data"]["version"]

        # 验证版本号递增
        assert new_version == initial_version + 1


class TestKnowledgePermissions:
    """知识库权限测试"""

    @pytest.mark.asyncio
    async def test_unauthorized_access(
        self, test_client: AsyncClient
    ):
        """测试未授权访问"""
        response = await test_client.get("/knowledge-bases")
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_invalid_token(
        self, test_client: AsyncClient
    ):
        """测试无效 token"""
        response = await test_client.get(
            "/knowledge-bases",
            headers={"Authorization": "Bearer invalid_token"}
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_get_nonexistent_knowledge_base(
        self, test_client: AsyncClient, test_token: str
    ):
        """测试获取不存在的知识库"""
        response = await test_client.get(
            "/knowledge-bases/nonexistent-id",
            headers={"Authorization": f"Bearer {test_token}"}
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_get_nonexistent_knowledge(
        self, test_client: AsyncClient, test_token: str
    ):
        """测试获取不存在的知识文档"""
        response = await test_client.get(
            "/knowledge/nonexistent-id",
            headers={"Authorization": f"Bearer {test_token}"}
        )
        assert response.status_code == 404


class TestKnowledgeStatistics:
    """知识库统计功能测试"""

    @pytest.mark.asyncio
    async def test_knowledge_base_statistics(
        self, test_client: AsyncClient, test_token: str, test_kb_id: str
    ):
        """测试知识库统计"""
        response = await test_client.get(
            f"/knowledge-bases/{test_kb_id}/statistics",
            headers={"Authorization": f"Bearer {test_token}"}
        )

        assert response.status_code == 200
        data = response.json()["data"]

        # 验证统计数据结构
        assert "total_knowledges" in data
        assert "published_count" in data
        assert "draft_count" in data


class TestKnowledgePagination:
    """知识文档分页测试"""

    @pytest.mark.asyncio
    async def test_pagination_default_page_size(
        self, test_client: AsyncClient, test_token: str
    ):
        """测试默认分页"""
        response = await test_client.get(
            "/knowledge",
            headers={"Authorization": f"Bearer {test_token}"}
        )

        assert response.status_code == 200
        data = response.json()

        assert "data" in data
        assert "total" in data["data"]
        assert "current" in data["data"]
        assert "pageSize" in data["data"]

    @pytest.mark.asyncio
    async def test_pagination_custom_page_size(
        self, test_client: AsyncClient, test_token: str
    ):
        """测试自定义分页大小"""
        response = await test_client.get(
            "/knowledge?pageSize=5",
            headers={"Authorization": f"Bearer {test_token}"}
        )

        assert response.status_code == 200
        data = response.json()["data"]

        # 验证返回不超过 pageSize
        assert len(data["rows"]) <= 5

    @pytest.mark.asyncio
    async def test_pagination_page_number(
        self, test_client: AsyncClient, test_token: str
    ):
        """测试分页页码"""
        response = await test_client.get(
            "/knowledge?current=1&pageSize=10",
            headers={"Authorization": f"Bearer {test_token}"}
        )

        assert response.status_code == 200
        data = response.json()

        assert data["data"]["current"] == 1


@pytest.mark.asyncio
async def test_knowledge_lifecycle(
    test_client: AsyncClient, test_token: str, test_kb_id: str
):
    """测试知识文档完整生命周期"""

    # 1. 创建草稿
    create_response = await test_client.post(
        "/knowledge",
        headers={"Authorization": f"Bearer {test_token}"},
        json={
            "title": "生命周期测试文档",
            "content": "# 草稿版本",
            "knowledgeBaseId": test_kb_id,
            "status": "draft"
        }
    )
    assert create_response.status_code == 200
    knowledge_id = create_response.json()["data"]["id"]
    initial_version = create_response.json()["data"]["version"]

    # 2. 更新内容
    update_response = await test_client.put(
        f"/knowledge/{knowledge_id}",
        headers={"Authorization": f"Bearer {test_token}"},
        json={
            "title": "生命周期测试文档 v2",
            "content": "# 更新版本\n\n这是更新后的内容"
        }
    )
    assert update_response.status_code == 200
    new_version = update_response.json()["data"]["version"]
    assert new_version == initial_version + 1

    # 3. 发布文档
    publish_response = await test_client.post(
        f"/knowledge/{knowledge_id}/publish",
        headers={"Authorization": f"Bearer {test_token}"}
    )
    assert publish_response.status_code == 200
    assert publish_response.json()["data"]["status"] == "published"

    # 4. 取消发布
    unpublish_response = await test_client.post(
        f"/knowledge/{knowledge_id}/unpublish",
        headers={"Authorization": f"Bearer {test_token}"}
    )
    assert unpublish_response.status_code == 200
    assert unpublish_response.json()["data"]["status"] == "draft"

    # 5. 删除文档
    delete_response = await test_client.delete(
        f"/knowledge/{knowledge_id}",
        headers={"Authorization": f"Bearer {test_token}"}
    )
    assert delete_response.status_code == 200

    # 6. 验证已删除
    get_response = await test_client.get(
        f"/knowledge/{knowledge_id}",
        headers={"Authorization": f"Bearer {test_token}"}
    )
    assert get_response.status_code == 404
