"""
Project API 测试配置

使用 config/test.yaml 配置文件

测试前准备：
1. 设置环境变量：export APP_ENV=test (Windows: $env:APP_ENV="test")
2. 确保 MySQL 服务运行并可访问
3. 运行测试：uv run pytest tests/project/test_project_api.py -v
"""

import os
import pytest
from typing import AsyncGenerator
from httpx import AsyncClient, ASGITransport

# 设置测试环境（必须在导入 app 之前）
os.environ["APP_ENV"] = "test"

from opentask.main import app


@pytest.fixture
async def test_client() -> AsyncGenerator[AsyncClient, None]:
    """测试客户端 fixture

    使用 ASGITransport 直接在内存中调用 FastAPI app，
    无需启动 uvicorn 服务器
    """
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test"
    ) as ac:
        yield ac


@pytest.fixture
async def test_token(test_client: AsyncClient) -> str:
    """获取测试 token"""
    response = await test_client.post(
        "/auth/login",
        json={"username": "admin", "password": "123456"}
    )
    assert response.status_code == 200, "Failed to login"
    data = response.json()
    return data["data"]["token"]


@pytest.fixture
async def test_project_id(test_client: AsyncClient, test_token: str) -> str:
    """创建测试项目并返回 ID"""
    # 先尝试获取现有项目
    response = await test_client.get(
        "/projects",
        headers={"Authorization": f"Bearer {test_token}"}
    )

    if response.status_code == 200:
        projects = response.json()["data"]
        if projects:
            # 返回第一个项目的 ID
            return projects[0]["id"]

    # 如果没有项目，创建一个
    response = await test_client.post(
        "/projects",
        headers={"Authorization": f"Bearer {test_token}"},
        json={
            "name": "测试项目 - Project自动化测试",
            "description": "用于自动化 Project 测试的项目",
        }
    )
    assert response.status_code == 200, "Failed to create test project"
    return response.json()["data"]["id"]


@pytest.fixture(autouse=True)
async def cleanup_test_data(test_client: AsyncClient, test_token: str = None):
    """每个测试后清理测试数据"""
    yield

    # 如果没有 test_token，跳过清理
    if test_token is None:
        return

    # 清理测试创建的项目
    try:
        response = await test_client.get(
            "/projects",
            headers={"Authorization": f"Bearer {test_token}"}
        )
        if response.status_code == 200:
            projects = response.json()["data"]
            for project in projects:
                # 只删除测试创建的项目
                if "自动化测试" in project.get("name", ""):
                    await test_client.delete(
                        f"/projects/{project['id']}",
                        headers={"Authorization": f"Bearer {test_token}"}
                    )
    except Exception as e:
        # 清理失败不应影响测试结果
        print(f"Warning: Cleanup failed: {e}")
