"""
Project API 测试

测试项目管理和仓库配置的 API 端点
"""

import pytest
from httpx import AsyncClient
from opentask.models.requirement.enums import MergeStatus


class TestProjectCRUD:
    """项目 CRUD 操作测试"""

    async def test_create_project_success(self, test_client: AsyncClient, test_token: str):
        """测试成功创建项目"""
        response = await test_client.post(
            "/api/projects",
            headers={"Authorization": f"Bearer {test_token}"},
            json={
                "name": "自动化测试项目",
                "description": "用于自动化测试的项目"
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200
        assert data["data"]["name"] == "自动化测试项目"
        assert data["data"]["description"] == "用于自动化测试的项目"
        assert "id" in data["data"]

    async def test_get_project_list(self, test_client: AsyncClient, test_token: str):
        """测试获取项目列表"""
        response = await test_client.get(
            "/api/projects",
            headers={"Authorization": f"Bearer {test_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200
        assert isinstance(data["data"], list)

    async def test_get_project_detail(self, test_client: AsyncClient, test_token: str, test_project_id: str):
        """测试获取项目详情"""
        response = await test_client.get(
            f"/api/projects/{test_project_id}",
            headers={"Authorization": f"Bearer {test_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200
        assert data["data"]["id"] == test_project_id

    async def test_update_project(self, test_client: AsyncClient, test_token: str, test_project_id: str):
        """测试更新项目"""
        response = await test_client.put(
            f"/api/projects/{test_project_id}",
            headers={"Authorization": f"Bearer {test_token}"},
            json={
                "name": "更新后的测试项目",
                "description": "更新后的描述"
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200
        assert data["data"]["name"] == "更新后的测试项目"

    async def test_delete_project(self, test_client: AsyncClient, test_token: str):
        """测试删除项目"""
        # 先创建一个测试项目
        create_response = await test_client.post(
            "/api/projects",
            headers={"Authorization": f"Bearer {test_token}"},
            json={
                "name": "待删除的测试项目",
                "description": "这个项目将被删除"
            }
        )
        project_id = create_response.json()["data"]["id"]

        # 删除项目
        response = await test_client.delete(
            f"/api/projects/{project_id}",
            headers={"Authorization": f"Bearer {test_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200

    async def test_get_project_list_active_only(self, test_client: AsyncClient, test_token: str):
        """测试只获取活跃项目"""
        response = await test_client.get(
            "/api/projects?active_only=true",
            headers={"Authorization": f"Bearer {test_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200
        # 验证返回的都是活跃项目
        for project in data["data"]:
            assert project["is_active"] is True


class TestRepoConfigCRUD:
    """仓库配置 CRUD 操作测试"""

    async def test_create_repo_config(self, test_client: AsyncClient, test_token: str, test_project_id: str):
        """测试创建仓库配置"""
        response = await test_client.post(
            f"/api/projects/{test_project_id}/repos",
            headers={"Authorization": f"Bearer {test_token}"},
            json={
                "name": "test-backend",
                "url": "https://github.com/test/backend.git",
                "main_branch": "main",
                "project_id": test_project_id
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200
        assert data["data"]["name"] == "test-backend"
        assert data["data"]["url"] == "https://github.com/test/backend.git"

    async def test_list_repo_configs(self, test_client: AsyncClient, test_token: str, test_project_id: str):
        """测试获取项目的仓库配置列表"""
        response = await test_client.get(
            f"/api/projects/{test_project_id}/repos",
            headers={"Authorization": f"Bearer {test_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200
        assert isinstance(data["data"], list)

    async def test_get_repo_config_detail(self, test_client: AsyncClient, test_token: str, test_project_id: str):
        """测试获取仓库配置详情"""
        # 先创建一个仓库配置
        create_response = await test_client.post(
            f"/api/projects/{test_project_id}/repos",
            headers={"Authorization": f"Bearer {test_token}"},
            json={
                "name": "test-frontend",
                "url": "https://github.com/test/frontend.git",
                "main_branch": "main",
                "project_id": test_project_id
            }
        )
        repo_id = create_response.json()["data"]["id"]

        # 获取仓库配置详情
        response = await test_client.get(
            f"/api/projects/{test_project_id}/repos/{repo_id}",
            headers={"Authorization": f"Bearer {test_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200
        assert data["data"]["id"] == repo_id

    async def test_update_repo_config(self, test_client: AsyncClient, test_token: str, test_project_id: str):
        """测试更新仓库配置"""
        # 先创建一个仓库配置
        create_response = await test_client.post(
            f"/api/projects/{test_project_id}/repos",
            headers={"Authorization": f"Bearer {test_token}"},
            json={
                "name": "test-api",
                "url": "https://github.com/test/api.git",
                "main_branch": "master",
                "project_id": test_project_id
            }
        )
        repo_id = create_response.json()["data"]["id"]

        # 更新仓库配置
        response = await test_client.put(
            f"/api/projects/{test_project_id}/repos/{repo_id}",
            headers={"Authorization": f"Bearer {test_token}"},
            json={
                "name": "test-api-updated",
                "main_branch": "main"
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200
        assert data["data"]["name"] == "test-api-updated"
        assert data["data"]["main_branch"] == "main"

    async def test_delete_repo_config(self, test_client: AsyncClient, test_token: str, test_project_id: str):
        """测试删除仓库配置"""
        # 先创建一个仓库配置
        create_response = await test_client.post(
            f"/api/projects/{test_project_id}/repos",
            headers={"Authorization": f"Bearer {test_token}"},
            json={
                "name": "test-temp",
                "url": "https://github.com/test/temp.git",
                "project_id": test_project_id
            }
        )
        repo_id = create_response.json()["data"]["id"]

        # 删除仓库配置
        response = await test_client.delete(
            f"/api/projects/{test_project_id}/repos/{repo_id}",
            headers={"Authorization": f"Bearer {test_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200


class TestRequirementRepoAssociation:
    """需求-仓库关联测试"""

    async def test_link_requirement_repo(self, test_client: AsyncClient, test_token: str, test_project_id: str):
        """测试关联需求和仓库"""
        # 先创建仓库配置
        repo_response = await test_client.post(
            f"/api/projects/{test_project_id}/repos",
            headers={"Authorization": f"Bearer {test_token}"},
            json={
                "name": "test-backend-2",
                "url": "https://github.com/test/backend2.git",
                "project_id": test_project_id
            }
        )
        repo_id = repo_response.json()["data"]["id"]

        # 创建需求
        req_response = await test_client.post(
            "/api/requirements",
            headers={"Authorization": f"Bearer {test_token}"},
            json={
                "title": "自动化测试需求 - 关联仓库",
                "description": "测试需求仓库关联",
                "project_id": test_project_id
            }
        )
        requirement_id = req_response.json()["data"]["id"]

        # 关联需求和仓库
        response = await test_client.post(
            "/api/projects/requirement-repos",
            headers={"Authorization": f"Bearer {test_token}"},
            json={
                "requirement_id": requirement_id,
                "repo_id": repo_id
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200
        assert data["data"]["requirement_id"] == requirement_id
        assert data["data"]["repo_id"] == repo_id

    async def test_get_requirement_repos(self, test_client: AsyncClient, test_token: str, test_project_id: str):
        """测试获取需求的所有仓库"""
        # 先创建需求
        req_response = await test_client.post(
            "/api/requirements",
            headers={"Authorization": f"Bearer {test_token}"},
            json={
                "title": "自动化测试需求 - 获取仓库",
                "description": "测试获取需求仓库",
                "project_id": test_project_id
            }
        )
        requirement_id = req_response.json()["data"]["id"]

        # 创建仓库配置
        repo_response = await test_client.post(
            f"/api/projects/{test_project_id}/repos",
            headers={"Authorization": f"Bearer {test_token}"},
            json={
                "name": "test-backend-3",
                "url": "https://github.com/test/backend3.git",
                "project_id": test_project_id
            }
        )
        repo_id = repo_response.json()["data"]["id"]

        # 关联需求和仓库
        await test_client.post(
            "/api/projects/requirement-repos",
            headers={"Authorization": f"Bearer {test_token}"},
            json={
                "requirement_id": requirement_id,
                "repo_id": repo_id
            }
        )

        # 获取需求的仓库列表
        response = await test_client.get(
            f"/api/projects/requirement-repos/{requirement_id}",
            headers={"Authorization": f"Bearer {test_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200
        assert isinstance(data["data"], list)

    async def test_update_requirement_repo(self, test_client: AsyncClient, test_token: str, test_project_id: str):
        """测试更新需求-仓库关联信息"""
        # 先创建需求
        req_response = await test_client.post(
            "/api/requirements",
            headers={"Authorization": f"Bearer {test_token}"},
            json={
                "title": "自动化测试需求 - 更新关联",
                "description": "测试更新需求仓库关联",
                "project_id": test_project_id
            }
        )
        requirement_id = req_response.json()["data"]["id"]

        # 创建仓库配置
        repo_response = await test_client.post(
            f"/api/projects/{test_project_id}/repos",
            headers={"Authorization": f"Bearer {test_token}"},
            json={
                "name": "test-backend-4",
                "url": "https://github.com/test/backend4.git",
                "project_id": test_project_id
            }
        )
        repo_id = repo_response.json()["data"]["id"]

        # 关联需求和仓库
        await test_client.post(
            "/api/projects/requirement-repos",
            headers={"Authorization": f"Bearer {test_token}"},
            json={
                "requirement_id": requirement_id,
                "repo_id": repo_id
            }
        )

        # 更新关联信息
        response = await test_client.put(
            f"/api/projects/requirement-repos/{requirement_id}/repos/{repo_id}",
            headers={"Authorization": f"Bearer {test_token}"},
            json={
                "branch": "feature/test-branch",
                "pr_url": "https://github.com/test/backend4/pull/1",
                "merge_status": MergeStatus.OPEN
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200
        assert data["data"]["branch"] == "feature/test-branch"
        assert data["data"]["pr_url"] == "https://github.com/test/backend4/pull/1"

    async def test_unlink_requirement_repo(self, test_client: AsyncClient, test_token: str, test_project_id: str):
        """测试取消需求和仓库的关联"""
        # 先创建需求
        req_response = await test_client.post(
            "/api/requirements",
            headers={"Authorization": f"Bearer {test_token}"},
            json={
                "title": "自动化测试需求 - 取消关联",
                "description": "测试取消需求仓库关联",
                "project_id": test_project_id
            }
        )
        requirement_id = req_response.json()["data"]["id"]

        # 创建仓库配置
        repo_response = await test_client.post(
            f"/api/projects/{test_project_id}/repos",
            headers={"Authorization": f"Bearer {test_token}"},
            json={
                "name": "test-backend-5",
                "url": "https://github.com/test/backend5.git",
                "project_id": test_project_id
            }
        )
        repo_id = repo_response.json()["data"]["id"]

        # 关联需求和仓库
        await test_client.post(
            "/api/projects/requirement-repos",
            headers={"Authorization": f"Bearer {test_token}"},
            json={
                "requirement_id": requirement_id,
                "repo_id": repo_id
            }
        )

        # 取消关联
        response = await test_client.delete(
            f"/api/projects/requirement-repos/{requirement_id}/repos/{repo_id}",
            headers={"Authorization": f"Bearer {test_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200


class TestProjectPermissions:
    """项目权限测试"""

    async def test_unauthorized_access(self, test_client: AsyncClient):
        """测试未授权访问"""
        response = await test_client.get("/api/projects")
        assert response.status_code == 401

    async def test_invalid_token(self, test_client: AsyncClient):
        """测试无效 token"""
        response = await test_client.get(
            "/api/projects",
            headers={"Authorization": "Bearer invalid_token"}
        )
        assert response.status_code == 401

    async def test_get_nonexistent_project(self, test_client: AsyncClient, test_token: str):
        """测试获取不存在的项目"""
        response = await test_client.get(
            "/api/projects/nonexistent-id",
            headers={"Authorization": f"Bearer {test_token}"}
        )
        assert response.status_code in [404, 400]  # 根据实际实现调整
