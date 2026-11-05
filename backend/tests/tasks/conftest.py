"""契约 API 测试配置（PostgreSQL，目录内自建 fixture）

- 覆盖引擎 URL 为 postgresql+asyncpg（不改全局 tests/conftest.py，PG 全局切换属另一 sprint）
- 建表用 DBModel.metadata.create_all；模型需显式导入（models 包 __init__ 不含 issue/tag/document/access_token）
- NullPool：asyncpg 连接绑定事件循环，函数级 fixture 各自持循环，避免跨循环复用连接
- 认证：client 覆盖 authenticate_contract（S5 契约层鉴权依赖）；
  raw_client 不覆盖——鉴权用例打真实依赖（vk_ API Key / JWT 对 PG 校验）

数据库：Docker opentask-pg（postgres:16，localhost:5432，opentask/opentask，测试库 opentask_test）。
"""

import os

# 测试环境 JWT 密钥（必须在 opentask 模块导入前设置；全局 conftest 已设，此处兜底）
os.environ.setdefault("AUTH_SECRET_KEY", "test-only-secret-key-do-not-use-in-prod")

import uuid
from datetime import datetime, timedelta
from typing import AsyncGenerator, Callable, Optional

import pytest
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
from opentask.models.access_token.model import AccessToken  # noqa: F401

from opentask.app import App
from opentask.api.tasks import mapping as contract_mapping
from opentask.api.tasks.auth import authenticate_contract
from opentask.models.base import DBModel
from opentask.models.issue.model import Issue
from opentask.models.user.model import UserModel
from opentask.repositories.base import get_session
from opentask.services.access_token.service import AccessTokenService
from opentask.models.access_token.schema import AccessTokenCreate

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
    """契约 API 的操作者（authenticate 覆盖返回它；reporter 默认落它）

    E98：创建个人默认可写 Workspace，使无头 create 可可靠绑定 KEY-N。
    """
    from opentask.services.workspace.service import WorkspaceService

    user = await _create_test_user(db, "tester")
    await WorkspaceService(db).create_for_owner(
        name=f"{user.username}-ws",
        owner_user_id=str(user.id),
    )
    await db.commit()
    yield user


@pytest_asyncio.fixture
async def assignee_user(
    db: AsyncSession, test_user: UserModel
) -> AsyncGenerator[UserModel, None]:
    """被分配人（验证 assignee 字符串 ID + metadata.username）

    E98：Issue 创建必带 workspace_id，assignee 必须是该 WS 成员（E71）。
    将 assignee 加入 test_user 的唯一可写 Workspace，避免邻面契约测回归。
    """
    from opentask.models.workspace.model import WorkspaceMember
    from opentask.services.workspace.issue_create_ws import list_writable_workspace_ids

    user = await _create_test_user(db, "assignee")
    wids = await list_writable_workspace_ids(db, str(test_user.id))
    assert len(wids) == 1, "test_user must have exactly one writable workspace"
    db.add(
        WorkspaceMember(
            workspace_id=wids[0],
            user_id=str(user.id),
            role="member",
        )
    )
    await db.commit()
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
    """HTTP 客户端：ASGITransport 直打契约端点，authenticate_contract 覆盖为测试用户"""
    async def override_authenticate_contract() -> UserModel:
        return test_user

    contract_app.dependency_overrides[authenticate_contract] = (
        override_authenticate_contract
    )
    async with AsyncClient(
        transport=ASGITransport(app=contract_app), base_url="http://test"
    ) as ac:
        yield ac


@pytest_asyncio.fixture
async def raw_client(contract_app: App) -> AsyncGenerator[AsyncClient, None]:
    """HTTP 客户端（不覆盖鉴权）：打真实 authenticate_contract（S5 鉴权用例）

    get_session 仍指向测试 PG；vk_ API Key / JWT 均对库校验。
    """
    async with AsyncClient(
        transport=ASGITransport(app=contract_app), base_url="http://test"
    ) as ac:
        yield ac


# ============================================================================
# 鉴权辅助：真实 Access Token（vk_）签发
# ============================================================================


async def create_api_key(db: AsyncSession, user: UserModel, name: str = "ct-key",
                         expires_days: int | None = None) -> str:
    """为用户签发真实 API Key（落 access_tokens 表，返回 vk_ 原文）

    expires_days 显式传入过去时间可造「已过期」token（401 用例）。
    """
    service = AccessTokenService(db)
    if expires_days is None:
        raw_token = (await service.create(str(user.id), AccessTokenCreate(name=name)))[1]
        return raw_token
    # 手工落行以精确控制过期时间（service.create 固定 365 天）
    import hashlib
    import secrets
    from opentask.services.access_token.service import TOKEN_PREFIX, TOKEN_BYTES
    raw_token = TOKEN_PREFIX + secrets.token_hex(TOKEN_BYTES)
    now = datetime.utcnow()
    db.add(
        AccessToken(
            user_id=str(user.id),
            name=name,
            token_hash=hashlib.sha256(raw_token.encode("utf-8")).hexdigest(),
            token_prefix=raw_token[:7],
            expires_at=now + timedelta(days=expires_days),
            created_at=now,
            updated_at=now,
        )
    )
    await db.commit()
    return raw_token


# ============================================================================
# 映射配置隔离：用例内注入 contract 配置，结束后恢复真实配置
# ============================================================================


@pytest.fixture
def mapping_config(monkeypatch: pytest.MonkeyPatch) -> Callable[[Optional[dict]], None]:
    """注入 contract 配置段并失效映射缓存；teardown 撤销注入并再次失效

    用法：mapping_config({"status_mapping": {...}, ...}) 或 mapping_config(None)
    （None = 模拟未配置任何 contract 段 → 代码默认表）。
    """
    def _set(cfg: Optional[dict]) -> None:
        if cfg is None:
            monkeypatch.setattr(contract_mapping, "load_config_file", lambda env: {})
        else:
            monkeypatch.setattr(
                contract_mapping, "load_config_file", lambda env: cfg
            )
        contract_mapping.reset_contract_mapping_cache()

    yield _set
    # monkeypatch 已撤销 load_config_file 注入；失效缓存让后续用例重读真实配置
    contract_mapping.reset_contract_mapping_cache()


# ============================================================================
# Seeding 辅助：直接落 Issue 行，精确控制 updated_at（游标边界测试需要）
# ============================================================================

_CT_SEED_SEQ = 800_000  # 高段但 < KEY_N_SEQ_CAP(1e6)，避免与业务 counter 撞


def next_seed_issue_code() -> str:
    """种子行的 issue_code：E99 仅 KEY-N（前缀 CT，序号远离业务 counter）。"""
    global _CT_SEED_SEQ
    _CT_SEED_SEQ += 1
    if _CT_SEED_SEQ >= 1_000_000:
        raise RuntimeError("contract seed issue_code sequence overflow")
    return f"CT-{_CT_SEED_SEQ}"


async def seed_issue(
    db: AsyncSession,
    *,
    title: str,
    status: str = "open",
    assignee_id: str | None = None,
    updated_at: datetime,
) -> Issue:
    """直接插入 Issue（绕过 service，精确控制时间戳）"""
    from opentask.models.workspace.model import Workspace
    from sqlalchemy import select as _select

    ws_id = (
        await db.execute(
            _select(Workspace.id).order_by(Workspace.created_at.asc(), Workspace.id.asc()).limit(1)
        )
    ).scalar_one_or_none()
    issue = Issue(
        issue_code=next_seed_issue_code(),
        title=title,
        description=None,
        type="bug",
        status=status,
        priority="medium",
        assignee_id=assignee_id,
        reporter_id="ct-seed",
        workspace_id=ws_id,
        created_at=updated_at,
        updated_at=updated_at,
    )
    db.add(issue)
    await db.commit()
    # 不 refresh（关系属性会过期）；列属性在 expire_on_commit=False 下仍可用
    return issue
