"""
文件存储和同步服务测试

测试文件优先架构的核心功能
"""

import pytest
import tempfile
import shutil
from pathlib import Path
from httpx import AsyncClient

# 文件优先架构已废弃：系统已迁移到 Git + Web 编辑架构 v2.0
# （见 opentask/app.py 注释与 docs/knowledge-base/GIT_WEB_ARCHITECTURE.md）。
# API 响应不再返回 file_path，文件同步/文件监控服务已下线，
# 本模块针对已下线的架构，整体跳过，待按新架构重写。
pytestmark = pytest.mark.skip(reason="文件优先架构已废弃（v2.0 Git+Web 编辑架构），用例待按新架构重写")


class TestFileStorage:
    """文件存储服务测试"""

    @pytest.mark.asyncio
    async def test_file_path_created(
        self, test_client: AsyncClient, test_token: str, test_kb_id: str
    ):
        """测试创建知识库时生成文件路径"""
        # 创建知识库
        response = await test_client.post(
            "/knowledge-bases",
            headers={"Authorization": f"Bearer {test_token}"},
            json={
                "name": "文件路径测试",
                "description": "测试文件路径生成"
            }
        )

        assert response.status_code == 200
        data = response.json()["data"]

        assert "file_path" in data
        assert data["file_path"] is not None
        assert len(data["file_path"]) > 0

        # 清理
        kb_id = data["id"]
        await test_client.delete(
            f"/knowledge-bases/{kb_id}",
            headers={"Authorization": f"Bearer {test_token}"}
        )

    @pytest.mark.asyncio
    async def test_knowledge_file_path(
        self, test_client: AsyncClient, test_token: str,
        test_kb_id: str, test_knowledge_id: str
    ):
        """测试知识文档的文件路径"""
        response = await test_client.get(
            f"/knowledge/{test_knowledge_id}",
            headers={"Authorization": f"Bearer {test_token}"}
        )

        assert response.status_code == 200
        data = response.json()["data"]

        assert "file_path" in data
        assert data["file_path"] is not None
        # 验证路径包含 .md 文件
        assert data["file_path"].endswith(".md")

    @pytest.mark.asyncio
    async def test_file_content_structure(
        self, test_client: AsyncClient, test_token: str,
        test_kb_id: str, test_knowledge_id: str
    ):
        """测试文件内容包含 front matter"""
        response = await test_client.get(
            f"/knowledge/{test_knowledge_id}",
            headers={"Authorization": f"Bearer {test_token}"}
        )

        assert response.status_code == 200
        data = response.json()["data"]

        assert "content" in data
        content = data["content"]

        # 验证包含 front matter
        assert "---" in content
        # 验证包含元数据字段
        assert "title:" in content or "id:" in content


class TestFileSync:
    """文件同步服务测试"""

    @pytest.mark.asyncio
    async def test_create_syncs_to_file(
        self, test_client: AsyncClient, test_token: str, test_kb_id: str
    ):
        """测试创建知识文档同步到文件"""
        response = await test_client.post(
            "/knowledge",
            headers={"Authorization": f"Bearer {test_token}"},
            json={
                "title": "同步测试文档",
                "content": "# 同步测试\n\n测试内容",
                "knowledgeBaseId": test_kb_id,
                "status": "draft"
            }
        )

        assert response.status_code == 200
        data = response.json()["data"]

        # 验证文件路径已设置
        assert "file_path" in data
        assert data["file_path"] is not None

        # 验证文件修改时间已更新
        assert "file_mtime" in data or "last_synced_at" in data

        # 清理
        knowledge_id = data["id"]
        await test_client.delete(
            f"/knowledge/{knowledge_id}",
            headers={"Authorization": f"Bearer {test_token}"}
        )

    @pytest.mark.asyncio
    async def test_update_syncs_to_file(
        self, test_client: AsyncClient, test_token: str, test_knowledge_id: str
    ):
        """测试更新知识文档同步到文件"""
        # 更新文档
        response = await test_client.put(
            f"/knowledge/{test_knowledge_id}",
            headers={"Authorization": f"Bearer {test_token}"},
            json={
                "title": "更新后的标题",
                "content": "# 更新后的内容\n\n新的内容"
            }
        )

        assert response.status_code == 200
        data = response.json()["data"]

        # 验证文件路径存在
        assert "file_path" in data

        # 验证内容已更新
        assert "更新后的内容" in data["content"]

    @pytest.mark.asyncio
    async def test_delete_removes_file(
        self, test_client: AsyncClient, test_token: str, test_kb_id: str
    ):
        """测试删除知识文档时删除文件"""
        # 创建文档
        create_response = await test_client.post(
            "/knowledge",
            headers={"Authorization": f"Bearer {test_token}"},
            json={
                "title": "将被删除的文档",
                "content": "测试删除文件",
                "knowledgeBaseId": test_kb_id
            }
        )

        knowledge_id = create_response.json()["data"]["id"]
        file_path = create_response.json()["data"]["file_path"]

        # 删除文档
        delete_response = await test_client.delete(
            f"/knowledge/{knowledge_id}",
            headers={"Authorization": f"Bearer {test_token}"}
        )

        assert delete_response.status_code == 200

        # 验证文件已删除（文件路径不再有效）
        # 注意：这个验证需要文件系统访问，API 可能不返回文件状态


class TestFileWatcher:
    """文件监控服务测试"""

    @pytest.mark.asyncio
    async def test_file_watcher_status(
        self, test_client: AsyncClient, test_token: str
    ):
        """测试文件监控服务状态"""
        # 这个测试需要管理员权限或专门的健康检查端点
        # 暂时跳过
        pytest.skip("需要专门的监控状态端点")


class TestFileIntegrity:
    """文件完整性测试"""

    @pytest.mark.asyncio
    async def test_database_file_consistency(
        self, test_client: AsyncClient, test_token: str,
        test_kb_id: str, test_knowledge_id: str
    ):
        """测试数据库和文件的一致性"""
        # 获取文档详情
        response = await test_client.get(
            f"/knowledge/{test_knowledge_id}",
            headers={"Authorization": f"Bearer {test_token}"}
        )

        assert response.status_code == 200
        data = response.json()["data"]

        # 验证文件路径存在
        assert "file_path" in data
        assert data["file_path"] is not None

        # 验证元数据存在
        assert "id" in data
        assert "title" in data
        assert "version" in data

        # 验证同步时间戳
        # 注意：这些字段可能不在 API 响应中
        # if "last_synced_at" in data:
        #     assert data["last_synced_at"] is not None

    @pytest.mark.asyncio
    async def test_file_mtime_tracking(
        self, test_client: AsyncClient, test_token: str,
        test_kb_id: str, test_knowledge_id: str
    ):
        """测试文件修改时间跟踪"""
        response = await test_client.get(
            f"/knowledge/{test_knowledge_id}",
            headers={"Authorization": f"Bearer {test_token}"}
        )

        assert response.status_code == 200
        data = response.json()["data"]

        # 验证文件修改时间存在（如果 API 返回）
        # 注意：这可能需要通过统计信息端点获取
        assert "id" in data
        assert "updated_at" in data


class TestFileFirstArchitecture:
    """文件优先架构集成测试"""

    @pytest.mark.asyncio
    async def test_create_kb_creates_directory(
        self, test_client: AsyncClient, test_token: str
    ):
        """测试创建知识库时创建目录"""
        response = await test_client.post(
            "/knowledge-bases",
            headers={"Authorization": f"Bearer {test_token}"},
            json={
                "name": "目录创建测试",
                "description": "测试目录创建"
            }
        )

        assert response.status_code == 200
        data = response.json()["data"]

        # 验证文件路径已设置
        assert "file_path" in data

        # 清理
        kb_id = data["id"]
        await test_client.delete(
            f"/knowledge-bases/{kb_id}",
            headers={"Authorization": f"Bearer {test_token}"}
        )

    @pytest.mark.asyncio
    async def test_create_knowledge_creates_file(
        self, test_client: AsyncClient, test_token: str, test_kb_id: str
    ):
        """测试创建知识文档时创建文件"""
        response = await test_client.post(
            "/knowledge",
            headers={"Authorization": f"Bearer {test_token}"},
            json={
                "title": "文件创建测试",
                "content": "# 测试内容",
                "knowledgeBaseId": test_kb_id
            }
        )

        assert response.status_code == 200
        data = response.json()["data"]

        # 验证文件路径已设置
        assert "file_path" in data
        assert data["file_path"].endswith(".md")

        # 清理
        knowledge_id = data["id"]
        await test_client.delete(
            f"/knowledge/{knowledge_id}",
            headers={"Authorization": f"Bearer {test_token}"}
        )

    @pytest.mark.asyncio
    async def test_full_sync_workflow(
        self, test_client: AsyncClient, test_token: str
    ):
        """测试完整的同步工作流"""
        # 1. 创建知识库
        kb_response = await test_client.post(
            "/knowledge-bases",
            headers={"Authorization": f"Bearer {test_token}"},
            json={
                "name": "同步工作流测试",
                "description": "完整工作流"
            }
        )
        assert kb_response.status_code == 200
        kb_id = kb_response.json()["data"]["id"]
        assert kb_response.json()["data"]["file_path"] is not None

        # 2. 创建文档
        doc_response = await test_client.post(
            "/knowledge",
            headers={"Authorization": f"Bearer {test_token}"},
            json={
                "title": "工作流测试文档",
                "content": "# 初始内容",
                "knowledgeBaseId": kb_id
            }
        )
        assert doc_response.status_code == 200
        knowledge_id = doc_response.json()["data"]["id"]
        assert doc_response.json()["data"]["file_path"] is not None

        # 3. 更新文档
        update_response = await test_client.put(
            f"/knowledge/{knowledge_id}",
            headers={"Authorization": f"Bearer {test_token}"},
            json={
                "title": "更新的标题",
                "content": "# 更新的内容"
            }
        )
        assert update_response.status_code == 200
        assert "file_path" in update_response.json()["data"]

        # 4. 发布文档
        publish_response = await test_client.post(
            f"/knowledge/{knowledge_id}/publish",
            headers={"Authorization": f"Bearer {test_token}"}
        )
        assert publish_response.status_code == 200

        # 5. 删除文档
        delete_response = await test_client.delete(
            f"/knowledge/{knowledge_id}",
            headers={"Authorization": f"Bearer {test_token}"}
        )
        assert delete_response.status_code == 200

        # 6. 删除知识库
        delete_kb_response = await test_client.delete(
            f"/knowledge-bases/{kb_id}",
            headers={"Authorization": f"Bearer {test_token}"}
        )
        assert delete_kb_response.status_code == 200


class TestFileContentValidation:
    """文件内容验证测试"""

    @pytest.mark.asyncio
    async def test_markdown_content_preserved(
        self, test_client: AsyncClient, test_token: str,
        test_kb_id: str, test_knowledge_id: str
    ):
        """测试 Markdown 内容正确保存"""
        markdown_content = """# 主标题

## 子标题

这是一段 **粗体** 文字和一段 *斜体* 文字。

- 列表项 1
- 列表项 2
- 列表项 3

```python
def hello():
    print("Hello, World!")
```

[链接](https://example.com)
"""

        # 创建文档
        create_response = await test_client.post(
            "/knowledge",
            headers={"Authorization": f"Bearer {test_token}"},
            json={
                "title": "Markdown 测试",
                "content": markdown_content,
                "knowledgeBaseId": test_kb_id
            }
        )

        assert create_response.status_code == 200
        knowledge_id = create_response.json()["data"]["id"]

        # 获取文档
        get_response = await test_client.get(
            f"/knowledge/{knowledge_id}",
            headers={"Authorization": f"Bearer {test_token}"}
        )

        assert get_response.status_code == 200
        data = get_response.json()["data"]

        # 验证内容完整
        assert "# 主标题" in data["content"]
        assert "**粗体**" in data["content"]
        assert "*斜体*" in data["content"]
        assert "```python" in data["content"]

        # 清理
        await test_client.delete(
            f"/knowledge/{knowledge_id}",
            headers={"Authorization": f"Bearer {test_token}"}
        )

    @pytest.mark.asyncio
    async def test_front_matter_generation(
        self, test_client: AsyncClient, test_token: str, test_kb_id: str
    ):
        """测试 Front Matter 元数据生成"""
        response = await test_client.post(
            "/knowledge",
            headers={"Authorization": f"Bearer {test_token}"},
            json={
                "title": "Front Matter 测试",
                "content": "# 内容",
                "knowledgeBaseId": test_kb_id,
                "status": "published"
            }
        )

        assert response.status_code == 200
        data = response.json()["data"]

        # 验证内容包含 front matter
        content = data["content"]
        assert "---" in content

        # 清理
        knowledge_id = data["id"]
        await test_client.delete(
            f"/knowledge/{knowledge_id}",
            headers={"Authorization": f"Bearer {test_token}"}
        )
