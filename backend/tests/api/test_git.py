"""
Git API 测试

测试范围：
- 初始化 Git 仓库 (/api/git/init/{kb_id})
- 获取 Git 状态 (/api/git/status/{kb_id})
- 提交变更 (/api/git/commit/{kb_id})
- 获取历史记录 (/api/git/history/{kb_id})
- 获取 diff (/api/git/diff/{kb_id}/{doc_id})
- 分支管理 (/api/git/branches/{kb_id}, /api/git/branch/{kb_id})
- 自动提交服务 (/api/git/auto-commit/start, /api/git/auto-commit/stop)
"""

import pytest
from unittest import mock
from httpx import AsyncClient


# ============================================================================
# 初始化 Git 仓库测试
# ============================================================================

@pytest.mark.asyncio
async def test_init_git_repo_success(test_client: AsyncClient):
    """测试初始化 Git 仓库成功"""
    # Mock GitService
    mock_repo = mock.Mock()
    mock_repo.bare = False
    mock_repo.heads = [mock.Mock(commit=mock.Mock(hexsha="abc123"))]

    with mock.patch("opentask.api.git.router.GitService") as mock_git_service:
        mock_service_instance = mock.Mock()
        mock_service_instance.init_repo.return_value = mock_repo
        mock_git_service.return_value = mock_service_instance

        response = await test_client.post("/api/git/init/test_kb_123")

        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200
        assert data["message"] == "Git 仓库初始化成功"
        assert data["data"]["kb_id"] == "test_kb_123"


@pytest.mark.asyncio
async def test_init_git_repo_already_exists(test_client: AsyncClient):
    """测试初始化已存在的 Git 仓库"""
    mock_repo = mock.Mock()
    mock_repo.bare = False

    with mock.patch("opentask.api.git.router.GitService") as mock_git_service:
        mock_service_instance = mock.Mock()
        mock_service_instance.init_repo.return_value = mock_repo
        mock_git_service.return_value = mock_service_instance

        response = await test_client.post("/api/git/init/existing_kb")

        assert response.status_code == 200


@pytest.mark.asyncio
async def test_init_git_repo_error(test_client: AsyncClient):
    """测试初始化 Git 仓库失败"""
    with mock.patch("opentask.api.git.router.GitService") as mock_git_service:
        mock_service_instance = mock.Mock()
        mock_service_instance.init_repo.side_effect = Exception("初始化失败")
        mock_git_service.return_value = mock_service_instance

        response = await test_client.post("/api/git/init/error_kb")

        assert response.status_code == 500


# ============================================================================
# Git 状态测试
# ============================================================================

@pytest.mark.asyncio
async def test_get_git_status_success(test_client: AsyncClient):
    """测试获取 Git 状态成功"""
    with mock.patch("opentask.api.git.router.GitService") as mock_git_service:
        mock_service_instance = mock.Mock()
        mock_service_instance.get_status.return_value = {
            "is_repo": True,
            "branch": "main",
            "is_dirty": False,
            "untracked": 0,
            "modified": 0
        }
        mock_git_service.return_value = mock_service_instance

        response = await test_client.get("/api/git/status/test_kb_123")

        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200
        assert data["data"]["is_repo"] is True


@pytest.mark.asyncio
async def test_get_git_status_not_repo(test_client: AsyncClient):
    """测试获取 Git 状态 - 不是 Git 仓库"""
    with mock.patch("opentask.api.git.router.GitService") as mock_git_service:
        mock_service_instance = mock.Mock()
        mock_service_instance.get_status.return_value = {
            "is_repo": False
        }
        mock_git_service.return_value = mock_service_instance

        response = await test_client.get("/api/git/status/not_repo_kb")

        assert response.status_code == 404


# ============================================================================
# 提交变更测试
# ============================================================================

@pytest.mark.asyncio
async def test_commit_changes_success(test_client: AsyncClient):
    """测试提交变更成功"""
    with mock.patch("opentask.api.git.router.GitService") as mock_git_service:
        mock_service_instance = mock.Mock()
        mock_service_instance.commit_changes.return_value = "abc123def456"
        mock_git_service.return_value = mock_service_instance

        response = await test_client.post(
            "/api/git/commit/test_kb_123",
            params={
                "message": "test commit",
                "author": "test_user"
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200
        assert data["message"] == "提交成功"
        assert data["data"]["commit_hash"] == "abc123def456"
        assert data["data"]["short_hash"] == "abc123de"


@pytest.mark.asyncio
async def test_commit_changes_no_changes(test_client: AsyncClient):
    """测试提交变更 - 没有变更"""
    with mock.patch("opentask.api.git.router.GitService") as mock_git_service:
        mock_service_instance = mock.Mock()
        mock_service_instance.commit_changes.return_value = None
        mock_git_service.return_value = mock_service_instance

        response = await test_client.post(
            "/api/git/commit/test_kb_123",
            params={
                "message": "test commit"
            }
        )

        assert response.status_code == 400


# ============================================================================
# 获取历史记录测试
# ============================================================================

@pytest.mark.asyncio
async def test_get_history_success(test_client: AsyncClient):
    """测试获取历史记录成功"""
    mock_history = [
        {
            "hash": "abc123",
            "author": "test_user",
            "date": "2024-01-01T00:00:00",
            "message": "test commit"
        }
    ]

    with mock.patch("opentask.api.git.router.GitService") as mock_git_service:
        mock_service_instance = mock.Mock()
        mock_service_instance.get_history.return_value = mock_history
        mock_git_service.return_value = mock_service_instance

        response = await test_client.get(
            "/api/git/history/test_kb_123",
            params={"limit": 10}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200
        assert len(data["data"]["history"]) == 1
        assert data["data"]["history"][0]["hash"] == "abc123"


@pytest.mark.asyncio
async def test_get_history_with_doc_id(test_client: AsyncClient):
    """测试获取特定文档的历史记录"""
    mock_history = [
        {
            "hash": "def456",
            "author": "test_user",
            "date": "2024-01-02T00:00:00",
            "message": "update doc"
        }
    ]

    with mock.patch("opentask.api.git.router.GitService") as mock_git_service:
        mock_service_instance = mock.Mock()
        mock_service_instance.get_history.return_value = mock_history
        mock_git_service.return_value = mock_service_instance

        response = await test_client.get(
            "/api/git/history/test_kb_123",
            params={
                "doc_id": "doc_123",
                "limit": 5
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert data["data"]["doc_id"] == "doc_123"


@pytest.mark.asyncio
async def test_get_history_limit_validation(test_client: AsyncClient):
    """测试获取历史记录 - limit 参数验证"""
    # limit 超过最大值
    response = await test_client.get(
        "/api/git/history/test_kb_123",
        params={"limit": 200}  # 超过最大值 100
    )

    # 应该返回验证错误
    assert response.status_code == 422


# ============================================================================
# 获取 diff 测试
# ============================================================================

@pytest.mark.asyncio
async def test_get_diff_success(test_client: AsyncClient):
    """测试获取文档 diff 成功"""
    mock_diff = {
        "doc_id": "doc_123",
        "old_content": "old line",
        "new_content": "new line",
        "diff": "--- old\n+++ new\n-old line\n+new line"
    }

    with mock.patch("opentask.api.git.router.GitService") as mock_git_service:
        mock_service_instance = mock.Mock()
        mock_service_instance.get_diff.return_value = mock_diff
        mock_git_service.return_value = mock_service_instance

        response = await test_client.get(
            "/api/git/diff/test_kb_123/doc_123"
        )

        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200
        assert "diff" in data["data"]


@pytest.mark.asyncio
async def test_get_diff_not_found(test_client: AsyncClient):
    """测试获取文档 diff - 文档不存在"""
    with mock.patch("opentask.api.git.router.GitService") as mock_git_service:
        mock_service_instance = mock.Mock()
        mock_service_instance.get_diff.return_value = None
        mock_git_service.return_value = mock_service_instance

        response = await test_client.get(
            "/api/git/diff/test_kb_123/nonexistent_doc"
        )

        assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_diff_with_commit_hash(test_client: AsyncClient):
    """测试获取文档 diff - 指定提交 hash"""
    mock_diff = {
        "doc_id": "doc_123",
        "diff": "test diff"
    }

    with mock.patch("opentask.api.git.router.GitService") as mock_git_service:
        mock_service_instance = mock.Mock()
        mock_service_instance.get_diff.return_value = mock_diff
        mock_git_service.return_value = mock_service_instance

        response = await test_client.get(
            "/api/git/diff/test_kb_123/doc_123",
            params={"commit_hash": "abc123"}
        )

        assert response.status_code == 200


# ============================================================================
# 分支管理测试
# ============================================================================

@pytest.mark.asyncio
async def test_list_branches_success(test_client: AsyncClient):
    """测试列出所有分支成功"""
    mock_branches = [
        {"name": "main", "is_head": True},
        {"name": "develop", "is_head": False},
        {"name": "feature/test", "is_head": False}
    ]

    with mock.patch("opentask.api.git.router.GitService") as mock_git_service:
        mock_service_instance = mock.Mock()
        mock_service_instance.list_branches.return_value = mock_branches
        mock_git_service.return_value = mock_service_instance

        response = await test_client.get("/api/git/branches/test_kb_123")

        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200
        assert len(data["data"]["branches"]) == 3


@pytest.mark.asyncio
async def test_create_branch_success(test_client: AsyncClient):
    """测试创建分支成功"""
    with mock.patch("opentask.api.git.router.GitService") as mock_git_service:
        mock_service_instance = mock.Mock()
        mock_service_instance.create_branch.return_value = True
        mock_git_service.return_value = mock_service_instance

        response = await test_client.post(
            "/api/git/branch/test_kb_123",
            params={"branch_name": "feature/new-feature"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200
        assert data["message"] == "分支创建成功"
        assert data["data"]["branch_name"] == "feature/new-feature"


@pytest.mark.asyncio
async def test_create_branch_failure(test_client: AsyncClient):
    """测试创建分支失败"""
    with mock.patch("opentask.api.git.router.GitService") as mock_git_service:
        mock_service_instance = mock.Mock()
        mock_service_instance.create_branch.return_value = False
        mock_git_service.return_value = mock_service_instance

        response = await test_client.post(
            "/api/git/branch/test_kb_123",
            params={"branch_name": "invalid/branch"}
        )

        assert response.status_code == 400


@pytest.mark.asyncio
async def test_create_branch_with_start_point(test_client: AsyncClient):
    """测试创建分支 - 指定起始点"""
    with mock.patch("opentask.api.git.router.GitService") as mock_git_service:
        mock_service_instance = mock.Mock()
        mock_service_instance.create_branch.return_value = True
        mock_git_service.return_value = mock_service_instance

        response = await test_client.post(
            "/api/git/branch/test_kb_123",
            params={
                "branch_name": "feature/from-tag",
                "start_point": "v1.0.0"
            }
        )

        assert response.status_code == 200


# ============================================================================
# 自动提交服务测试
# ============================================================================

@pytest.mark.asyncio
async def test_start_auto_commit(test_client: AsyncClient):
    """测试启动自动提交服务"""
    response = await test_client.post(
        "/api/git/auto-commit/start",
        params={"interval": 300}
    )

    assert response.status_code == 200
    data = response.json()
    assert data["code"] == 200
    assert data["data"]["interval"] == 300
    assert data["data"]["status"] == "configured"


@pytest.mark.asyncio
async def test_start_auto_commit_interval_validation(test_client: AsyncClient):
    """测试启动自动提交 - interval 参数验证"""
    # interval 小于最小值
    response = await test_client.post(
        "/api/git/auto-commit/start",
        params={"interval": 30}  # 小于 60
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_stop_auto_commit(test_client: AsyncClient):
    """测试停止自动提交服务"""
    response = await test_client.post("/api/git/auto-commit/stop")

    assert response.status_code == 200
    data = response.json()
    assert data["code"] == 200
    assert "已停止" in data["message"]
