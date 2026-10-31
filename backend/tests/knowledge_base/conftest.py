"""
知识库模块测试配置

使用 httpx.AsyncClient 和 ASGITransport 进行测试
"""

import os
import pytest
from typing import AsyncGenerator
from httpx import AsyncClient, ASGITransport

# 设置测试环境（必须在导入 app 之前）
os.environ["APP_ENV"] = "test"

from opentask.main import app


# 配置 pytest-asyncio
def pytest_configure(config):
    """启用 asyncio 模式"""
    config.option.asyncio_mode = "auto"


@pytest.fixture
async def test_client(seeded_users) -> AsyncGenerator[AsyncClient, None]:
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
        "/api/auth/login",
        json={"userName": "admin", "password": "123456"}
    )
    assert response.status_code == 200, "Failed to login"
    data = response.json()
    return data["data"]["token"]


@pytest.fixture
async def test_kb_id(test_client: AsyncClient, test_token: str) -> str:
    """创建测试知识库"""
    response = await test_client.post(
        "/api/knowledge-bases",
        headers={"Authorization": f"Bearer {test_token}"},
        json={
            "name": "测试知识库",
            "description": "自动化测试用知识库",
            "icon": "📚"
        }
    )

    assert response.status_code == 200
    kb_id = response.json()["data"]["id"]

    yield kb_id

    # 清理：删除测试知识库
    await test_client.delete(
        f"/api/knowledge-bases/{kb_id}",
        headers={"Authorization": f"Bearer {test_token}"}
    )


@pytest.fixture
async def test_knowledge_id(
    test_client: AsyncClient,
    test_token: str,
    test_kb_id: str
) -> str:
    """创建测试知识文档"""
    response = await test_client.post(
        "/api/knowledge",
        headers={"Authorization": f"Bearer {test_token}"},
        json={
            "title": "测试文档",
            "content": "# 测试文档内容\n\n这是一个测试文档。",
            "knowledge_base_id": test_kb_id,
            "status": "draft"
        }
    )

    assert response.status_code == 200
    knowledge_id = response.json()["data"]["id"]

    yield knowledge_id

    # 清理：删除测试文档
    await test_client.delete(
        f"/api/knowledge/{knowledge_id}",
        headers={"Authorization": f"Bearer {test_token}"}
    )


@pytest.fixture(autouse=True)
async def cleanup_test_data(test_client: AsyncClient, test_token: str = None):
    """每个测试后清理测试数据"""
    yield

    # 如果没有 test_token，跳过清理
    if test_token is None:
        return

    # 清理测试创建的知识文档
    try:
        response = await test_client.get(
            "/api/knowledge?search=自动化测试",
            headers={"Authorization": f"Bearer {test_token}"}
        )
        if response.status_code == 200:
            knowledges = response.json()["data"]["rows"]
            for knowledge in knowledges:
                # 只删除测试创建的知识文档
                if "自动化测试" in knowledge.get("title", ""):
                    await test_client.delete(
                        f"/api/knowledge/{knowledge['id']}",
                        headers={"Authorization": f"Bearer {test_token}"}
                    )
    except Exception as e:
        # 清理失败不应影响测试结果
        print(f"Warning: Cleanup failed: {e}")
