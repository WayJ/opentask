"""
Requirement API 测试配置

使用 config/test.yaml 配置文件

测试前准备：
1. 设置环境变量：export APP_ENV=test (Windows: $env:APP_ENV="test")
2. 确保 MySQL 服务运行并可访问
3. 运行测试：uv run pytest tests/requirement/test_requirement_api.py -v
"""

import os
import pytest
from typing import AsyncGenerator
from httpx import AsyncClient, ASGITransport

# 设置测试环境（必须在导入 app 之前）
os.environ["APP_ENV"] = "test"

from opentask.main import app


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
async def test_project_id(test_client: AsyncClient, test_token: str) -> str:
    """创建测试项目并返回 ID"""
    # 先尝试获取现有项目
    response = await test_client.get(
        "/api/projects",
        headers={"Authorization": f"Bearer {test_token}"}
    )

    if response.status_code == 200:
        projects = response.json()["data"]
        if projects:
            # 返回第一个项目的 ID
            return projects[0]["id"]

    # 如果没有项目，创建一个
    response = await test_client.post(
        "/api/projects",
        headers={"Authorization": f"Bearer {test_token}"},
        json={
            "name": "测试项目 - Requirement自动化测试",
            "description": "用于自动化 Requirement 测试的项目",
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

    # 清理测试创建的 Requirement
    try:
        response = await test_client.get(
            "/api/requirements?search=自动化测试",
            headers={"Authorization": f"Bearer {test_token}"}
        )
        if response.status_code == 200:
            data = response.json()["data"]
            requirements = data.get("data", []) if isinstance(data, dict) else data
            for requirement in requirements:
                # 只删除测试创建的 Requirement
                if isinstance(requirement, dict) and "自动化测试" in requirement.get("title", ""):
                    await test_client.delete(
                        f"/api/requirements/{requirement['id']}",
                        headers={"Authorization": f"Bearer {test_token}"}
                    )
    except Exception as e:
        # 清理失败不应影响测试结果
        print(f"Warning: Cleanup failed: {e}")


# ============================================================================
# 本地文件存储替身：文档上传依赖对象存储（MinIO），测试环境无 MinIO 容器
# ============================================================================

class _LocalFakeStorage:
    """与 MinIOStorageService 同接口的本地文件存储替身"""

    def __init__(self):
        import tempfile
        self.root = tempfile.mkdtemp(prefix="opentask_test_uploads_")

    async def save_upload_file(self, file, subdir=""):
        import os
        import uuid
        directory = subdir or "."
        os.makedirs(os.path.join(self.root, directory), exist_ok=True)
        content = await file.read()
        filename = file.filename or "upload.bin"
        stored = os.path.join(directory, f"{uuid.uuid4().hex}_{filename}").replace("\\", "/")
        with open(os.path.join(self.root, stored), "wb") as f:
            f.write(content)
        return stored, filename, len(content)

    def delete_file(self, path):
        import os
        full = os.path.join(self.root, path)
        if os.path.exists(full):
            os.remove(full)

    def file_exists(self, path):
        import os
        return os.path.exists(os.path.join(self.root, path))

    def get_file_stream(self, path):
        return open(os.path.join(self.root, path), "rb")

    def get_file_path(self, path):
        import os
        return os.path.join(self.root, path)


@pytest.fixture(autouse=True)
def _fake_storage(monkeypatch):
    """为 requirement 路由注入本地存储替身（仅影响测试进程）"""
    # 注意：包 __init__ 里 `from .router import router` 会让
    # `import opentask.api.requirement.router as x` 拿到 APIRouter 对象，
    # 必须经 importlib 取模块本身
    import importlib
    requirement_router = importlib.import_module("opentask.api.requirement.router")
    storage = _LocalFakeStorage()
    monkeypatch.setattr(requirement_router, "get_storage_service", lambda: storage)
    yield
