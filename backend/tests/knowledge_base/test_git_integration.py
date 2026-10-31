"""
知识库 Git 集成测试

测试 Git 版本控制相关的所有功能
"""

import pytest
import tempfile
import shutil
from pathlib import Path
from httpx import AsyncClient


class TestGitRepository:
    """Git 仓库管理测试"""

    @pytest.mark.asyncio
    async def test_init_git_repository(
        self, test_client: AsyncClient, test_token: str, test_kb_id: str
    ):
        """测试初始化 Git 仓库"""
        response = await test_client.post(
            f"/git/init/{test_kb_id}",
            headers={"Authorization": f"Bearer {test_token}"}
        )

        assert response.status_code == 200
        data = response.json()["data"]

        assert "head" in data  # 当前提交 hash
        assert data["is_repo"] == True

    @pytest.mark.asyncio
    async def test_get_git_status(
        self, test_client: AsyncClient, test_token: str, test_kb_id: str
    ):
        """测试获取 Git 状态"""
        # 先初始化仓库
        await test_client.post(
            f"/git/init/{test_kb_id}",
            headers={"Authorization": f"Bearer {test_token}"}
        )

        # 获取状态
        response = await test_client.get(
            f"/git/status/{test_kb_id}",
            headers={"Authorization": f"Bearer {test_token}"}
        )

        assert response.status_code == 200
        data = response.json()["data"]

        assert data["is_repo"] == True
        assert "branch" in data
        assert "dirty" in data
        assert "untracked" in data
        assert "modified" in data
        assert "staged" in data


class TestGitCommit:
    """Git 提交功能测试"""

    @pytest.mark.asyncio
    async def test_commit_changes(
        self, test_client: AsyncClient, test_token: str, test_kb_id: str
    ):
        """测试提交变更"""
        # 初始化仓库
        await test_client.post(
            f"/git/init/{test_kb_id}",
            headers={"Authorization": f"Bearer {test_token}"}
        )

        # 提交变更
        response = await test_client.post(
            f"/git/commit/{test_kb_id}?message=测试提交",
            headers={"Authorization": f"Bearer {test_token}"}
        )

        assert response.status_code == 200
        data = response.json()["data"]

        assert "commit_hash" in data
        assert "short_hash" in data
        assert len(data["short_hash"]) == 8  # Git short hash 格式

    @pytest.mark.asyncio
    async def test_commit_with_custom_message(
        self, test_client: AsyncClient, test_token: str, test_kb_id: str
    ):
        """测试使用自定义消息提交"""
        # 初始化仓库
        await test_client.post(
            f"/git/init/{test_kb_id}",
            headers={"Authorization": f"Bearer {test_token}"}
        )

        # 使用自定义消息提交
        custom_message = "feat: 添加新功能"
        response = await test_client.post(
            f"/git/commit/{test_kb_id}?message={custom_message}",
            headers={"Authorization": f"Bearer {test_token}"}
        )

        assert response.status_code == 200

        # 验证提交历史中包含该消息
        history_response = await test_client.get(
            f"/git/history/{test_kb_id}",
            headers={"Authorization": f"Bearer {test_token}"}
        )

        history = history_response.json()["data"]["history"]
        assert len(history) > 0
        assert custom_message in history[0]["message"]


class TestGitHistory:
    """Git 历史记录测试"""

    @pytest.mark.asyncio
    async def test_get_commit_history(
        self, test_client: AsyncClient, test_token: str, test_kb_id: str
    ):
        """测试获取提交历史"""
        # 初始化仓库并创建几个提交
        await test_client.post(
            f"/git/init/{test_kb_id}",
            headers={"Authorization": f"Bearer {test_token}"}
        )

        await test_client.post(
            f"/git/commit/{test_kb_id}?message=第一次提交",
            headers={"Authorization": f"Bearer {test_token}"}
        )

        await test_client.post(
            f"/git/commit/{test_kb_id}?message=第二次提交",
            headers={"Authorization": f"Bearer {test_token}"}
        )

        # 获取历史
        response = await test_client.get(
            f"/git/history/{test_kb_id}?limit=10",
            headers={"Authorization": f"Bearer {test_token}"}
        )

        assert response.status_code == 200
        data = response.json()["data"]

        assert "history" in data
        assert len(data["history"]) >= 2

        # 验证历史记录结构
        for commit in data["history"]:
            assert "commit_hash" in commit
            assert "short_hash" in commit
            assert "message" in commit
            assert "author" in commit
            assert "date" in commit

    @pytest.mark.asyncio
    async def test_get_history_for_document(
        self, test_client: AsyncClient, test_token: str,
        test_kb_id: str, test_knowledge_id: str
    ):
        """测试获取特定文档的历史"""
        # 初始化仓库
        await test_client.post(
            f"/git/init/{test_kb_id}",
            headers={"Authorization": f"Bearer {test_token}"}
        )

        # 获取文档历史
        response = await test_client.get(
            f"/git/history/{test_kb_id}?doc_id={test_knowledge_id}",
            headers={"Authorization": f"Bearer {test_token}"}
        )

        assert response.status_code == 200
        data = response.json()["data"]

        assert "history" in data

    @pytest.mark.asyncio
    async def test_history_limit(
        self, test_client: AsyncClient, test_token: str, test_kb_id: str
    ):
        """测试历史记录数量限制"""
        # 初始化仓库
        await test_client.post(
            f"/git/init/{test_kb_id}",
            headers={"Authorization": f"Bearer {test_token}"}
        )

        # 请求限制数量的历史
        response = await test_client.get(
            f"/git/history/{test_kb_id}?limit=5",
            headers={"Authorization": f"Bearer {test_token}"}
        )

        assert response.status_code == 200
        data = response.json()["data"]

        assert len(data["history"]) <= 5


class TestGitDiff:
    """Git 差异比较测试"""

    @pytest.mark.asyncio
    async def test_get_document_diff(
        self, test_client: AsyncClient, test_token: str,
        test_kb_id: str, test_knowledge_id: str
    ):
        """测试获取文档差异"""
        # 初始化仓库
        await test_client.post(
            f"/git/init/{test_kb_id}",
            headers={"Authorization": f"Bearer {test_token}"}
        )

        # 修改文档
        await test_client.put(
            f"/knowledge/{test_knowledge_id}",
            headers={"Authorization": f"Bearer {test_token}"},
            json={
                "title": "修改后的标题",
                "content": "# 新内容\n\n这是修改后的内容"
            }
        )

        # 获取 diff
        response = await test_client.get(
            f"/git/diff/{test_kb_id}/{test_knowledge_id}",
            headers={"Authorization": f"Bearer {test_token}"}
        )

        assert response.status_code == 200
        data = response.json()["data"]

        assert "commit_hash" in data or data is None  # 可能没有变更

    @pytest.mark.asyncio
    async def test_get_diff_for_commit(
        self, test_client: AsyncClient, test_token: str,
        test_kb_id: str, test_knowledge_id: str
    ):
        """测试获取特定提交的差异"""
        # 初始化仓库并提交
        await test_client.post(
            f"/git/init/{test_kb_id}",
            headers={"Authorization": f"Bearer {test_token}"}
        )

        commit_response = await test_client.post(
            f"/git/commit/{test_kb_id}?message=初始提交",
            headers={"Authorization": f"Bearer {test_token}"}
        )
        commit_hash = commit_response.json()["data"]["commit_hash"]

        # 获取该提交的 diff
        response = await test_client.get(
            f"/git/diff/{test_kb_id}/{test_knowledge_id}?commit_hash={commit_hash}",
            headers={"Authorization": f"Bearer {test_token}"}
        )

        assert response.status_code == 200


class TestGitBranches:
    """Git 分支管理测试"""

    @pytest.mark.asyncio
    async def test_list_branches(
        self, test_client: AsyncClient, test_token: str, test_kb_id: str
    ):
        """测试列出所有分支"""
        # 初始化仓库
        await test_client.post(
            f"/git/init/{test_kb_id}",
            headers={"Authorization": f"Bearer {test_token}"}
        )

        # 列出分支
        response = await test_client.get(
            f"/git/branches/{test_kb_id}",
            headers={"Authorization": f"Bearer {test_token}"}
        )

        assert response.status_code == 200
        data = response.json()["data"]

        assert "branches" in data
        assert len(data["branches"]) > 0

        # 验证分支结构
        for branch in data["branches"]:
            assert "name" in branch
            assert "short_hash" in branch
            assert "is_active" in branch
            assert "message" in branch

    @pytest.mark.asyncio
    async def test_create_branch(
        self, test_client: AsyncClient, test_token: str, test_kb_id: str
    ):
        """测试创建新分支"""
        # 初始化仓库
        await test_client.post(
            f"/git/init/{test_kb_id}",
            headers={"Authorization": f"Bearer {test_token}"}
        )

        # 创建新分支
        branch_name = "feature/test-branch"
        response = await test_client.post(
            f"/git/branch/{test_kb_id}?branch_name={branch_name}",
            headers={"Authorization": f"Bearer {test_token}"}
        )

        assert response.status_code == 200

        # 验证分支已创建
        list_response = await test_client.get(
            f"/git/branches/{test_kb_id}",
            headers={"Authorization": f"Bearer {test_token}"}
        )

        branches = list_response.json()["data"]["branches"]
        branch_names = [b["name"] for b in branches]
        assert branch_name in branch_names

    @pytest.mark.asyncio
    async def test_create_branch_from_start_point(
        self, test_client: AsyncClient, test_token: str, test_kb_id: str
    ):
        """测试从指定起始点创建分支"""
        # 初始化仓库并提交
        await test_client.post(
            f"/git/init/{test_kb_id}",
            headers={"Authorization": f"Bearer {test_token}"}
        )

        commit_response = await test_client.post(
            f"/git/commit/{test_kb_id}?message=初始提交",
            headers={"Authorization": f"Bearer {test_token}"}
        )
        start_point = commit_response.json()["data"]["short_hash"]

        # 从起始点创建分支
        branch_name = "feature/from-start"
        response = await test_client.post(
            f"/git/branch/{test_kb_id}?branch_name={branch_name}&start_point={start_point}",
            headers={"Authorization": f"Bearer {test_token}"}
        )

        assert response.status_code == 200


class TestGitWorkflow:
    """Git 工作流测试"""

    @pytest.mark.asyncio
    async def test_complete_git_workflow(
        self, test_client: AsyncClient, test_token: str,
        test_kb_id: str, test_knowledge_id: str
    ):
        """测试完整的 Git 工作流"""

        # 1. 初始化仓库
        init_response = await test_client.post(
            f"/git/init/{test_kb_id}",
            headers={"Authorization": f"Bearer {test_token}"}
        )
        assert init_response.status_code == 200

        # 2. 初始提交
        commit1_response = await test_client.post(
            f"/git/commit/{test_kb_id}?message=初始版本",
            headers={"Authorization": f"Bearer {test_token}"}
        )
        assert commit1_response.status_code == 200
        commit1_hash = commit1_response.json()["data"]["commit_hash"]

        # 3. 修改文档
        await test_client.put(
            f"/knowledge/{test_knowledge_id}",
            headers={"Authorization": f"Bearer {test_token}"},
            json={
                "title": "第一次修改",
                "content": "# 修改后的内容"
            }
        )

        # 4. 提交修改
        commit2_response = await test_client.post(
            f"/git/commit/{test_kb_id}?message=第一次修改",
            headers={"Authorization": f"Bearer {test_token}"}
        )
        assert commit2_response.status_code == 200

        # 5. 创建分支
        branch_response = await test_client.post(
            f"/git/branch/{test_kb_id}?branch_name=feature/experiment",
            headers={"Authorization": f"Bearer {test_token}"}
        )
        assert branch_response.status_code == 200

        # 6. 查看历史
        history_response = await test_client.get(
            f"/git/history/{test_kb_id}?limit=10",
            headers={"Authorization": f"Bearer {test_token}"}
        )
        assert history_response.status_code == 200
        history = history_response.json()["data"]["history"]
        assert len(history) >= 2

        # 7. 查看 diff
        diff_response = await test_client.get(
            f"/git/diff/{test_kb_id}/{test_knowledge_id}",
            headers={"Authorization": f"Bearer {test_token}"}
        )
        assert diff_response.status_code == 200

        # 8. 列出分支
        branches_response = await test_client.get(
            f"/git/branches/{test_kb_id}",
            headers={"Authorization": f"Bearer {test_token}"}
        )
        assert branches_response.status_code == 200
        branches = branches_response.json()["data"]["branches"]
        branch_names = [b["name"] for b in branches]
        assert "feature/experiment" in branch_names

        # 9. 查看状态
        status_response = await test_client.get(
            f"/git/status/{test_kb_id}",
            headers={"Authorization": f"Bearer {test_token}"}
        )
        assert status_response.status_code == 200
        status = status_response.json()["data"]
        assert status["is_repo"] == True


class TestGitPermissions:
    """Git 权限测试"""

    @pytest.mark.asyncio
    async def test_git_operations_require_auth(
        self, test_client: AsyncClient
    ):
        """测试 Git 操作需要认证"""
        response = await test_client.get("/git/status/test-kb-id")
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_git_operations_with_invalid_token(
        self, test_client: AsyncClient
    ):
        """测试使用无效 token 进行 Git 操作"""
        response = await test_client.get(
            "/git/status/test-kb-id",
            headers={"Authorization": "Bearer invalid_token"}
        )
        assert response.status_code == 401
