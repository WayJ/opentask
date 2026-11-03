"""
Issue Collection API 测试配置
"""
import os
import pytest_asyncio
from typing import AsyncGenerator
from httpx import AsyncClient, ASGITransport

# 设置测试环境
os.environ["APP_ENV"] = "test"

from opentask.main import app
from sqlalchemy import select
from passlib.context import CryptContext
from opentask.repositories.base import SessionCreator
from opentask.models.user.model import UserModel

# 密码哈希上下文（bcrypt），与 opentask.auth 保持一致
_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


@pytest_asyncio.fixture
async def test_client(seeded_users) -> AsyncGenerator[AsyncClient, None]:
    """测试客户端 fixture"""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test"
    ) as ac:
        yield ac


@pytest_asyncio.fixture
async def test_client_with_user(test_client: AsyncClient) -> AsyncClient:
    """创建测试用户并返回客户端"""
    async with SessionCreator() as session:
        # 检查测试用户是否已存在
        result = await session.execute(
            select(UserModel).where(UserModel.name == "admin")
        )
        user = result.scalar_one_or_none()

        # 如果不存在，创建测试用户
        if not user:
            user = UserModel(
                name="admin",
                sso_name="管理员",
                password_hash=_pwd_context.hash("123456"),  # bcrypt 哈希
                email="admin@test.com"
            )
            session.add(user)
            await session.commit()
            await session.refresh(user)
            print(f"✓ 创建测试用户: admin (ID: {user.id})")
        else:
            # 如果用户存在但没有密码哈希，设置密码哈希
            if not user.password_hash:
                user.password_hash = _pwd_context.hash("123456")
                await session.commit()
                print(f"✓ 更新测试用户密码: admin")
            else:
                print(f"✓ 测试用户已存在: admin (ID: {user.id})")

    return test_client


@pytest_asyncio.fixture
async def test_token(test_client_with_user: AsyncClient) -> str:
    """获取测试 token（使用本地登录接口）"""
    # 使用本地登录接口，不需要加密密码
    response = await test_client_with_user.post(
        "/api/auth/login-local",
        json={"userName": "admin", "password": "123456"}
    )
    assert response.status_code == 200, f"Failed to login: {response.text}"
    data = response.json()
    return data["data"]["token"]


@pytest_asyncio.fixture(autouse=True)
async def cleanup_test_data(test_client: AsyncClient, test_token: str = None):
    """每个测试后清理测试数据"""
    yield

    # 如果没有 test_token，跳过清理
    if test_token is None:
        return

    # 清理测试创建的问题集
    try:
        response = await test_client.get(
            "/api/issues/collections?search=自动化测试",
            headers={"Authorization": f"Bearer {test_token}"}
        )
        if response.status_code == 200:
            collections = response.json()["data"]["rows"]
            for collection in collections:
                # 只删除测试创建的问题集
                if "自动化测试" in collection.get("title", ""):
                    await test_client.delete(
                        f"/api/issues/collections/{collection['id']}",
                        headers={"Authorization": f"Bearer {test_token}"}
                    )
    except Exception as e:
        print(f"Warning: Cleanup failed: {e}")
