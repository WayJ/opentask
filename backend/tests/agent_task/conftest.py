"""
Agent Task 测试配置

继承主测试配置，添加 Agent Task 特定的 fixtures
"""

import pytest
from typing import AsyncGenerator
from httpx import AsyncClient

# 导入主测试配置的 fixtures
from tests.conftest import test_session, test_client, test_token


@pytest.fixture(autouse=True)
async def cleanup_test_data(test_client: AsyncClient, test_token: str = None):
    """每个测试后清理测试数据"""
    yield

    if test_token is None:
        return

    # 清理测试创建的任务
    try:
        response = await test_client.get(
            "/api/tasks",
            headers={"Authorization": f"Bearer {test_token}"}
        )
        if response.status_code == 200:
            data = response.json()["data"]
            tasks = data.get("rows", [])
            for task in tasks:
                # 只删除测试创建的任务
                if isinstance(task, dict) and "测试" in task.get("title", ""):
                    await test_client.delete(
                        f"/api/tasks/{task['task_id']}",
                        headers={"Authorization": f"Bearer {test_token}"}
                    )
    except Exception as e:
        print(f"Warning: Cleanup failed: {e}")
