"""
OpenTask 统一测试配置

提供：
1. 统一的数据库配置
2. 测试用户管理
3. 测试 fixtures
"""

import os

# 测试环境 JWT 密钥（必须在 opentask 模块导入前设置，jwt_utils 在 import 时读取）
os.environ.setdefault("AUTH_SECRET_KEY", "test-only-secret-key-do-not-use-in-prod")

# 跳过已废弃的测试模块（引用不存在的旧路径）
collect_ignore = [
    "agent_task/test_agent_task_service.py",
    "agent_task/test_repository.py",
    "agent_task/test_service_async.py",
    "agent_task/test_agent_task_api.py",
    "agent_task/run_service_tests.py",
    "agent_task/conftest_standalone.py",
    "test_issues_api.py",
]
import asyncio
from typing import AsyncGenerator, Generator
from unittest import mock
from datetime import timedelta, datetime

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from opentask.app import App
from opentask.models.base import DBModel
from opentask.repositories.base import get_session
from opentask.config import config
from opentask.models.user.model import UserModel
from opentask.models.tag.model import Tag  # 导入 Tag 模型，确保它被包含在 metadata 中
from opentask.jwt_utils import create_access_token


# ============================================================================
# 测试数据库配置
# ============================================================================

TEST_DB_HOST = config.mysql_host
TEST_DB_PORT = config.mysql_port
TEST_DB_USER = config.mysql_user
TEST_DB_PASSWORD = config.mysql_password
TEST_DB_NAME = os.getenv("MYSQL_TEST_DATABASE", "opentask_test")

from urllib.parse import quote_plus
encoded_password = quote_plus(TEST_DB_PASSWORD)
TEST_DATABASE_URL = f"mysql+aiomysql://{TEST_DB_USER}:{encoded_password}@{TEST_DB_HOST}:{TEST_DB_PORT}/{TEST_DB_NAME}"


# ============================================================================
# 测试用户配置
# ============================================================================

TEST_USERS = {
    "admin": {
        "username": "admin",
        "password": "123456",
        "is_superuser": True
    },
    "jiangwei": {
        "username": "jiangwei",
        "password": "123456",
        "is_superuser": False
    }
}


# ============================================================================
# Pytest 配置
# ============================================================================

def pytest_addoption(parser):
    """添加 pytest 命令行选项"""
    parser.addoption("--run-expensive", action="store_true", default=False,
                     help="run expensive tests")
    parser.addoption("--use-jnpf", action="store_true", default=False,
                     help="use real JNPF service (default: use mock)")


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]):
    """标记测试"""
    if not config.getoption("--run-expensive"):
        skip_expensive = pytest.mark.skip(reason="need --run-expensive option to run")
        for item in items:
            if "expensive" in item.keywords:
                item.add_marker(skip_expensive)


# ============================================================================
# Fixtures: 数据库引擎
# ============================================================================

@pytest_asyncio.fixture(scope="session")
async def test_engine() -> AsyncGenerator[AsyncEngine, None]:
    """创建测试数据库引擎（会话级）

    使用 NullPool 避免连接池 reset 导致的事件循环问题
    """
    from sqlalchemy.pool import NullPool

    engine = create_async_engine(
        TEST_DATABASE_URL,
        echo=False,
        poolclass=NullPool,  # 禁用连接池，避免 reset 问题
        connect_args={
            "charset": "utf8mb4",
        }
    )

    # 创建所有必要的表（仅一次）
    try:
        async with engine.begin() as conn:
            from opentask.models.base import DBModel
            await conn.run_sync(lambda sync_conn: DBModel.metadata.create_all(sync_conn, checkfirst=True))
            print(f"[OK] Test database ({TEST_DB_NAME}) tables created")
    except Exception as e:
        import logging
        logging.error(f"Table creation failed: {e}", exc_info=True)
        raise

    yield engine

    # 测试会话结束后清理（删除所有表）
    try:
        async with engine.begin() as conn:
            from opentask.models.base import DBModel
            await conn.run_sync(lambda sync_conn: DBModel.metadata.drop_all(sync_conn))
            print(f"[OK] Test database ({TEST_DB_NAME}) tables cleaned")
    except Exception as e:
        import logging
        logging.warning(f"Table cleanup failed: {e}")

    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def test_session(test_engine: AsyncEngine) -> AsyncGenerator[AsyncSession, None]:
    """创建测试数据库会话（函数级）

    注意：
    - 不使用事务回滚，避免与 service 层的 commit 冲突
    - 测试后使用 delete 清理数据
    """
    async_session_maker = sessionmaker(
        test_engine, class_=AsyncSession, expire_on_commit=False, autocommit=False
    )

    async with async_session_maker() as session:
        yield session

    # 测试结束后清理数据（在 session 关闭后）
    async with async_session_maker() as cleanup_session:
        try:
            from sqlalchemy import delete
            from opentask.models.task.model import Task

            # 删除所有测试创建的任务
            await cleanup_session.execute(delete(Task).where(Task.requirement_id.like("test-%")))
            await cleanup_session.commit()
            print("  [OK] Test data cleaned")
        except Exception as e:
            print(f"  [WARNING] Error cleaning test data: {e}")
            # 尝试回滚
            try:
                await cleanup_session.rollback()
            except Exception:
                pass


# ============================================================================
# Fixtures: 测试客户端
# ============================================================================

@pytest.fixture(scope="session")
def app():
    """创建 FastAPI app 实例"""
    return App()


@pytest.fixture
async def test_client(app) -> AsyncGenerator[AsyncClient, None]:
    """创建测试 HTTP 客户端"""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test"
    ) as client:
        yield client


# ============================================================================
# Fixtures: 测试认证
# ============================================================================

@pytest.fixture
async def test_token() -> str:
    """获取测试 token（使用 mock）"""
    token = create_access_token(
        data={"sub": "jiangwei", "is_superuser": False},
        expires_delta=timedelta(hours=24)
    )
    return token


@pytest.fixture
def admin_token() -> str:
    """管理员测试 token"""
    return create_access_token(
        data={"sub": "admin", "is_superuser": True},
        expires_delta=timedelta(hours=24)
    )


# ============================================================================
# Fixtures: 测试数据
# ============================================================================

@pytest_asyncio.fixture
async def test_requirement(test_session: AsyncSession):
    """创建测试需求数据"""
    from opentask.models.requirement.model import Requirement
    import uuid

    requirement = Requirement(
        id=str(uuid.uuid4()),
        code=f"TEST-REQ-{datetime.now().strftime('%Y%m%d%H%M%S')}",
        title="测试需求",
        description="这是一个测试需求",
        status="draft",
        priority="medium",
        created_by="test_user",
        created_at=datetime.utcnow()
    )

    test_session.add(requirement)
    await test_session.commit()
    await test_session.refresh(requirement)

    yield requirement

    # 清理
    await test_session.delete(requirement)
    await test_session.commit()

