"""
OpenTask API Client 业务方法测试

测试范围：
- Project API
- Issue API
- Auth API
- Requirement API
- Collection API
"""

import pytest
from unittest import mock

from opentask.utils.api_client import OpenTaskClient, APIError


# ============================================================================
# Project API 测试
# ============================================================================

class TestProjectAPI:
    """测试 Project API 方法"""

    @pytest.mark.asyncio
    async def test_list_projects(self):
        """测试列出项目"""
        client = OpenTaskClient()

        with mock.patch.object(client, 'get') as mock_get:
            # API 返回带 rows 字段的响应
            mock_get.return_value = {
                "rows": [
                    {"id": "1", "name": "Project A"},
                    {"id": "2", "name": "Project B"}
                ],
                "total": 2
            }

            result = await client.list_projects(active_only=True)

            # list_projects 返回完整的响应对象
            assert "rows" in result
            assert len(result["rows"]) == 2
            assert result["rows"][0]["name"] == "Project A"
            mock_get.assert_called_once_with("/api/projects", params={"active_only": True})

    @pytest.mark.asyncio
    async def test_list_projects_empty(self):
        """测试列出项目 - 空列表"""
        client = OpenTaskClient()

        with mock.patch.object(client, 'get') as mock_get:
            # API 返回带 rows 字段的响应（即使是空的）
            mock_get.return_value = {
                "rows": [],
                "total": 0
            }

            projects = await client.list_projects()

            # 应该返回空列表
            assert projects == {"rows": [], "total": 0} or projects == []

    @pytest.mark.asyncio
    async def test_get_project(self):
        """测试获取项目详情"""
        client = OpenTaskClient()

        with mock.patch.object(client, 'get') as mock_get:
            mock_get.return_value = {"id": "1", "name": "Test Project"}

            project = await client.get_project("1")

            assert project["name"] == "Test Project"
            mock_get.assert_called_once_with("/api/projects/1")

    @pytest.mark.asyncio
    async def test_create_project(self):
        """测试创建项目"""
        client = OpenTaskClient()

        with mock.patch.object(client, 'post') as mock_post:
            mock_post.return_value = {"id": "new-1", "name": "New Project"}

            project = await client.create_project("New Project", "Test Description")

            assert project["name"] == "New Project"
            mock_post.assert_called_once_with("/api/projects", data={
                "name": "New Project",
                "description": "Test Description"
            })

    @pytest.mark.asyncio
    async def test_update_project(self):
        """测试更新项目"""
        client = OpenTaskClient()

        with mock.patch.object(client, 'put') as mock_put:
            mock_put.return_value = {"id": "1", "name": "Updated Name"}

            project = await client.update_project("1", name="Updated Name")

            assert project["name"] == "Updated Name"
            mock_put.assert_called_once_with("/api/projects/1", data={"name": "Updated Name"})

    @pytest.mark.asyncio
    async def test_delete_project(self):
        """测试删除项目"""
        client = OpenTaskClient()

        with mock.patch.object(client, 'delete') as mock_delete:
            mock_delete.return_value = True

            result = await client.delete_project("1")

            assert result is True
            mock_delete.assert_called_once_with("/api/projects/1")


# ============================================================================
# Issue API 测试
# ============================================================================

class TestIssueAPI:
    """测试 Issue API 方法"""

    @pytest.mark.asyncio
    async def test_list_issues(self):
        """测试列出 Issue"""
        client = OpenTaskClient()

        with mock.patch.object(client, 'get') as mock_get:
            mock_get.return_value = {
                "rows": [{"id": "1", "title": "Issue 1"}],
                "total": 1
            }

            result = await client.list_issues(page=1, status="open")

            assert result["total"] == 1
            mock_get.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_issue(self):
        """测试获取 Issue 详情"""
        client = OpenTaskClient()

        with mock.patch.object(client, 'get') as mock_get:
            mock_get.return_value = {"id": "1", "title": "Test Issue"}

            issue = await client.get_issue("1")

            assert issue["title"] == "Test Issue"
            mock_get.assert_called_once_with("/api/issues/1", params={})

    @pytest.mark.asyncio
    async def test_get_issue_by_code(self):
        """测试根据 Issue Code 获取"""
        client = OpenTaskClient()

        with mock.patch.object(client, 'get') as mock_get:
            mock_get.return_value = {"id": "1", "issue_code": "OT-1"}

            issue = await client.get_issue("OT-1", by_code=True)

            assert issue["issue_code"] == "OT-1"
            mock_get.assert_called_once_with("/api/issues/OT-1", params={"by_code": "true"})

    @pytest.mark.asyncio
    async def test_create_issue(self):
        """测试创建 Issue"""
        client = OpenTaskClient()

        with mock.patch.object(client, 'post') as mock_post:
            mock_post.return_value = {"id": "new-1", "title": "New Issue"}

            issue = await client.create_issue(
                title="New Issue",
                description="Test",
                type="bug",
                priority="high"
            )

            assert issue["title"] == "New Issue"
            mock_post.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_issue_status(self):
        """测试更新 Issue 状态"""
        client = OpenTaskClient()

        with mock.patch.object(client, 'put') as mock_put:
            mock_put.return_value = {"id": "1", "status": "closed"}

            issue = await client.update_issue_status("1", "closed")

            assert issue["status"] == "closed"
            mock_put.assert_called_once_with("/api/issues/1/status", params={"status": "closed"})

    @pytest.mark.asyncio
    async def test_add_comment(self):
        """测试添加评论"""
        client = OpenTaskClient()

        with mock.patch.object(client, 'post') as mock_post:
            mock_post.return_value = {"id": "comment-1", "content": "Test comment"}

            comment = await client.add_comment("1", "Test comment")

            assert comment["content"] == "Test comment"
            mock_post.assert_called_once_with("/api/issues/1/comments", data={"content": "Test comment"})

    @pytest.mark.asyncio
    async def test_get_comments(self):
        """测试获取评论列表"""
        client = OpenTaskClient()

        with mock.patch.object(client, 'get') as mock_get:
            mock_get.return_value = {
                "rows": [
                    {"id": "c1", "content": "Comment 1"},
                    {"id": "c2", "content": "Comment 2"}
                ]
            }

            comments = await client.get_comments("1")

            assert len(comments) == 2
            assert comments[0]["content"] == "Comment 1"


# ============================================================================
# Auth API 测试
# ============================================================================

class TestAuthAPI:
    """测试 Auth API 方法"""

    @pytest.mark.asyncio
    async def test_login(self):
        """测试登录"""
        client = OpenTaskClient()

        with mock.patch.object(client, 'post') as mock_post:
            mock_post.return_value = {
                "access_token": "token123",
                "user": {"id": "1", "username": "test"}
            }

            result = await client.login("testuser", "password")

            assert result["access_token"] == "token123"
            mock_post.assert_called_once_with("/api/auth/login", data={
                "userName": "testuser",
                "password": "password"
            })

    @pytest.mark.asyncio
    async def test_get_me(self):
        """测试获取当前用户信息"""
        client = OpenTaskClient()

        with mock.patch.object(client, 'get') as mock_get:
            mock_get.return_value = {"id": "1", "username": "test"}

            user = await client.get_me()

            assert user["username"] == "test"
            # 使用正确的 API 路径
            mock_get.assert_called_once_with("/api/auth/getUserInfo")


# ============================================================================
# Requirement API 测试
# ============================================================================

class TestRequirementAPI:
    """测试 Requirement API 方法"""

    @pytest.mark.asyncio
    async def test_list_requirements(self):
        """测试列出需求"""
        client = OpenTaskClient()

        with mock.patch.object(client, 'get') as mock_get:
            mock_get.return_value = {
                "rows": [{"id": "1", "title": "Req 1"}],
                "total": 1
            }

            result = await client.list_requirements(page=1, status="pending")

            assert result["total"] == 1
            mock_get.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_requirement(self):
        """测试创建需求"""
        client = OpenTaskClient()

        with mock.patch.object(client, 'post') as mock_post:
            mock_post.return_value = {"id": "new-1", "title": "New Req"}

            req = await client.create_requirement(
                title="New Req",
                description="Test",
                priority="high"
            )

            assert req["title"] == "New Req"
            mock_post.assert_called_once()

    @pytest.mark.asyncio
    async def test_search_requirements(self):
        """测试搜索需求"""
        client = OpenTaskClient()

        with mock.patch.object(client, 'get') as mock_get:
            mock_get.return_value = [
                {"id": "1", "title": "Search Result 1"},
                {"id": "2", "title": "Search Result 2"}
            ]

            results = await client.search_requirements("test", limit=10)

            assert len(results) == 2
            mock_get.assert_called_once_with("/api/requirements/search", params={
                "q": "test",
                "limit": 10
            })


# ============================================================================
# Collection API 测试
# ============================================================================

class TestCollectionAPI:
    """测试 Collection API 方法"""

    @pytest.mark.asyncio
    async def test_list_collections(self):
        """测试列出集合"""
        client = OpenTaskClient()

        with mock.patch.object(client, 'get') as mock_get:
            mock_get.return_value = {
                "rows": [{"id": "1", "title": "Collection 1"}],
                "total": 1
            }

            result = await client.list_collections(page=1)

            assert result["total"] == 1
            mock_get.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_collection(self):
        """测试创建集合"""
        client = OpenTaskClient()

        with mock.patch.object(client, 'post') as mock_post:
            mock_post.return_value = {"id": "new-1", "title": "New Collection"}

            collection = await client.create_collection("New Collection", "Test")

            assert collection["title"] == "New Collection"
            mock_post.assert_called_once_with("/api/issue-collections", data={
                "title": "New Collection",
                "description": "Test",
                "status": "draft"
            })

    @pytest.mark.asyncio
    async def test_get_collection_statistics(self):
        """测试获取集合统计"""
        client = OpenTaskClient()

        with mock.patch.object(client, 'get') as mock_get:
            mock_get.return_value = {
                "total_issues": 10,
                "parsed_issues": 5,
                "failed_issues": 1
            }

            stats = await client.get_collection_statistics("1")

            assert stats["total_issues"] == 10
            mock_get.assert_called_once_with("/api/issue-collections/1/statistics")

    @pytest.mark.asyncio
    async def test_parse_collection(self):
        """测试解析集合"""
        client = OpenTaskClient()

        with mock.patch.object(client, 'post') as mock_post:
            mock_post.return_value = {
                "parsed_count": 5,
                "issue_ids": ["i1", "i2", "i3", "i4", "i5"]
            }

            result = await client.parse_collection("1", [
                {"title": "Issue 1"},
                {"title": "Issue 2"}
            ])

            assert result["parsed_count"] == 5
            mock_post.assert_called_once_with("/api/issue-collections/1/parse", data={
                "issues": [{"title": "Issue 1"}, {"title": "Issue 2"}]
            })


# ============================================================================
# Conversation API 测试
# ============================================================================

class TestConversationAPI:
    """测试 Conversation API 方法"""

    @pytest.mark.asyncio
    async def test_list_conversations(self):
        """测试列出对话"""
        client = OpenTaskClient()

        with mock.patch.object(client, 'get') as mock_get:
            mock_get.return_value = [
                {"id": "1", "title": "Chat 1"},
                {"id": "2", "title": "Chat 2"}
            ]

            conversations = await client.list_conversations()

            assert len(conversations) == 2
            mock_get.assert_called_once_with("/api/conversations")

    @pytest.mark.asyncio
    async def test_create_conversation(self):
        """测试创建对话"""
        client = OpenTaskClient()

        with mock.patch.object(client, 'post') as mock_post:
            mock_post.return_value = {"id": "new-1", "title": "New Chat"}

            conv = await client.create_conversation("New Chat")

            assert conv["title"] == "New Chat"
            mock_post.assert_called_once_with("/api/conversations", data={"title": "New Chat"})

    @pytest.mark.asyncio
    async def test_send_message(self):
        """测试发送消息"""
        client = OpenTaskClient()

        with mock.patch.object(client, 'post') as mock_post:
            mock_post.return_value = {
                "id": "msg-1",
                "content": "Hello",
                "role": "user"
            }

            msg = await client.send_message("conv-1", "Hello")

            assert msg["content"] == "Hello"
            mock_post.assert_called_once_with("/api/conversations/conv-1/message", data={
                "content": "Hello"
            })

    @pytest.mark.asyncio
    async def test_get_conversation_history(self):
        """测试获取对话历史"""
        client = OpenTaskClient()

        with mock.patch.object(client, 'get') as mock_get:
            mock_get.return_value = [
                {"role": "user", "content": "Hi"},
                {"role": "assistant", "content": "Hello"}
            ]

            history = await client.get_conversation_history("conv-1")

            assert len(history) == 2
            mock_get.assert_called_once_with("/api/conversations/conv-1/history")


# ============================================================================
# Git API 测试
# ============================================================================

class TestGitAPI:
    """测试 Git API 方法"""

    @pytest.mark.asyncio
    async def test_git_clone(self):
        """测试 Git 克隆"""
        client = OpenTaskClient()

        with mock.patch.object(client, 'post') as mock_post:
            mock_post.return_value = {"success": True, "path": "/repo"}

            result = await client.git_clone("https://github.com/test/repo.git", "/repo")

            assert result["success"] is True
            mock_post.assert_called_once_with("/api/git/clone", data={
                "url": "https://github.com/test/repo.git",
                "path": "/repo"
            })

    @pytest.mark.asyncio
    async def test_git_status(self):
        """测试 Git 状态"""
        client = OpenTaskClient()

        with mock.patch.object(client, 'get') as mock_get:
            mock_get.return_value = {
                "branch": "main",
                "modified": ["file1.txt"]
            }

            status = await client.git_status("/repo")

            assert status["branch"] == "main"
            mock_get.assert_called_once_with("/api/git/status", params={"path": "/repo"})

    @pytest.mark.asyncio
    async def test_git_commit(self):
        """测试 Git 提交"""
        client = OpenTaskClient()

        with mock.patch.object(client, 'post') as mock_post:
            mock_post.return_value = {"commit": "abc123"}

            result = await client.git_commit("/repo", "Test commit")

            assert result["commit"] == "abc123"
            mock_post.assert_called_once_with("/api/git/commit", data={
                "path": "/repo",
                "message": "Test commit"
            })

    @pytest.mark.asyncio
    async def test_git_push(self):
        """测试 Git 推送"""
        client = OpenTaskClient()

        with mock.patch.object(client, 'post') as mock_post:
            mock_post.return_value = {"success": True}

            result = await client.git_push("/repo")

            assert result["success"] is True
            mock_post.assert_called_once_with("/api/git/push", data={"path": "/repo"})
