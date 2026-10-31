"""契约 API 测试配置（PostgreSQL，目录内自建 fixture）

- 覆盖引擎 URL 为 postgresql+asyncpg（不改全局 tests/conftest.py，PG 全局切换属另一 sprint）
- 建表用 DBModel.metadata.create_all；模型需显式导入（models 包 __init__ 不含 issue/tag/document）
- NullPool：asyncpg 连接绑定事件循环，函数级 fixture 各自持循环，避免跨循环复用连接
- 认证：dependency_overrides 覆盖 authenticate（access_token 鉴权接入属 S5，此处仅骨架）

数据库：Docker opentask-pg（postgres:16，localhost:5432，opentask/opentask，测试库 opentask_test）。
"""

import os

# 测试环境 JWT 密钥（必须在 opentask 模块导入前设置；全局 conftest 已设，此处兜底）
os.environ.setdefault("AUTH_SECRET_KEY", "test-only-secret-key-do-not-use-in-prod")

import uuid
from datetime import datetime
from typing import AsyncGenerator

import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

# 显式导入全部模型（见模块 docstring；顺序在 setdefault 之后）
import opentask.repositories.base  # noqa: F401  加载其余模型进 metadata
from opentask.models.issue import model as _issue_model  # noqa: F401
from opentask.models.tag.model import Tag  # noqa: F401
from opentask.models.document.model import Document  # noqa: F401

from opentask.app import App
from opentask.auth import authenticate
from opentask.models.base import DBModel
from opentask.models.issue.model import Issue
from opentask.models.user.model import UserModel
from opentask.repositories.base import get_session

# PostgreSQL 连接串（可用环境变量覆盖）
PG_TEST_DATABASE_URL = os.getenv(
    "OPENTASK_TASKS_TEST_DB_URL",
    "postgresql+asyncpg://opentask:opentask@localhost:5432/opentask_test",
)

# 测试数据统一前缀，便于清理与隔离（并行 worker 共库时互不干扰）
TITLE_PREFIX = "CT-"
LABEL_PREFIX = "ct-"
USER_USERNAME_PREFIX = "ct_user_"


@pytest_asyncio.fixture
async def pg_engine() -> AsyncGenerator[AsyncEngine, None]:
    """PostgreSQL 测试引擎（函数级 + NullPool，见模块 docstring）"""
    engine = create_async_engine(PG_TEST_DATABASE_URL, echo=False, poolclass=NullPool)
    async with engine.begin() as conn:
        await conn.run_sync(
            lambda sync_conn: DBModel.metadata.create_all(sync_conn, checkfirst=True)
        )
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def db(pg_engine: AsyncEngine) -> AsyncGenerator[AsyncSession, None]:
    """直连会话：测试内 seeding 与落库断言用"""
    maker = async_sessionmaker(
        pg_engine, class_=AsyncSession, expire_on_commit=False, autocommit=False
    )
    async with maker() as session:
        yield session


@pytest_asyncio.fixture(autouse=True)
async def cleanup_contract_rows(db: AsyncSession) -> AsyncGenerator[None, None]:
    """每个测试后按前缀清理契约测试数据（不 drop 表，避免影响共库的其他测试）"""
    yield
    try:
        await db.execute(delete(Issue).where(Issue.title.like(f"{TITLE_PREFIX}%")))
        await db.execute(delete(Tag).where(Tag.name.like(f"{LABEL_PREFIX}%")))
        await db.execute(
            delete(UserModel).where(
                UserModel.username.like(f"{USER_USERNAME_PREFIX}%")
            )
        )
        await db.commit()
    except Exception as e:  # 清理失败不影响测试结论
        print(f"[WARNING] contract test cleanup failed: {e}")
        await db.rollback()


async def _create_test_user(db: AsyncSession, base_name: str) -> UserModel:
    user = UserModel(
        name=f"{base_name}显示名",
        username=f"{USER_USERNAME_PREFIX}{base_name}_{uuid.uuid4().hex[:8]}",
        status=1,
    )
    db.add(user)
    await db.commit()
    # 不 refresh：refresh 会触发关系属性过期，async 下 repr/访问会 MissingGreenlet；
    # expire_on_commit=False 保证列属性仍可用，id 为客户端默认值已回填
    return user


@pytest_asyncio.fixture
async def test_user(db: AsyncSession) -> AsyncGenerator[UserModel, None]:
    """契约 API 的操作者（authenticate 覆盖返回它；reporter 默认落它）"""
    user = await _create_test_user(db, "tester")
    yield user


@pytest_asyncio.fixture
async def assignee_user(db: AsyncSession) -> AsyncGenerator[UserModel, None]:
    """被分配人（验证 assignee 字符串 ID + metadata.username）"""
    user = await _create_test_user(db, "assignee")
    yield user


@pytest_asyncio.fixture
async def contract_app(pg_engine: AsyncEngine) -> AsyncGenerator[App, None]:
    """契约测试用 App：get_session 覆盖到 PG 引擎"""
    maker = async_sessionmaker(
        pg_engine, class_=AsyncSession, expire_on_commit=False, autocommit=False
    )

    async def override_get_session() -> AsyncGenerator[AsyncSession, None]:
        session = maker()
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

    app = App()
    app.dependency_overrides[get_session] = override_get_session
    yield app
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def client(
    contract_app: App, test_user: UserModel
) -> AsyncGenerator[AsyncClient, None]:
    """HTTP 客户端：ASGITransport 直打契约端点，authenticate 覆盖为测试用户"""
    async def override_authenticate() -> UserModel:
        return test_user

    contract_app.dependency_overrides[authenticate] = override_authenticate
    async with AsyncClient(
        transport=ASGITransport(app=contract_app), base_url="http://test"
    ) as ac:
        yield ac


# ============================================================================
# Seeding 辅助：直接落 Issue 行，精确控制 updated_at（游标边界测试需要）
# ============================================================================

_CT_SEED_SEQ = 900_000_000  # 远离业务序号段，避免与 _generate_issue_code 冲突


def next_seed_issue_code() -> str:
    """种子行的 issue_code：数字后缀（_generate_issue_code 按 CAST INT 取 max，
    非数字后缀会让后续 POST 的 CAST 报错，因此必须用数字）"""
    global _CT_SEED_SEQ
    _CT_SEED_SEQ += 1
    return f"ISSUE{datetime.now().year}-{_CT_SEED_SEQ}"


async def seed_issue(
    db: AsyncSession,
    *,
    title: str,
    status: str = "open",
    assignee_id: str | None = None,
    updated_at: datetime,
) -> Issue:
    """直接插入 Issue（绕过 service，精确控制时间戳）"""
    issue = Issue(
        issue_code=next_seed_issue_code(),
        title=title,
        description=None,
        type="bug",
        status=status,
        priority="medium",
        assignee_id=assignee_id,
        reporter_id="ct-seed",
        created_at=updated_at,
        updated_at=updated_at,
    )
    db.add(issue)
    await db.commit()
    # 不 refresh（关系属性会过期）；列属性在 expire_on_commit=False 下仍可用
    return issue
