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

# 应用侧数据库必须指向测试库：repositories.base 在 import 时创建模块级引擎，
# 引擎 URL 取自 config.database_dsn_async（env POSTGRES_DATABASE > yaml database.postgres.database）。
# 必须在导入任何 opentask 模块之前固定，否则应用会读写开发库 opentask，
# 测试通过 test_session 播种的用户对应用不可见（登录链 401 / 用户不存在级联）。
TEST_DB_NAME = os.getenv("POSTGRES_TEST_DATABASE", "opentask_test")
os.environ.setdefault("POSTGRES_DATABASE", TEST_DB_NAME)

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
from urllib.parse import quote_plus

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool

from opentask.config import config


# ============================================================================
# 测试数据库配置
# ============================================================================

TEST_DB_HOST = config.postgres_host
TEST_DB_PORT = config.postgres_port
TEST_DB_USER = config.postgres_user
TEST_DB_PASSWORD = config.postgres_password

encoded_password = quote_plus(TEST_DB_PASSWORD)
TEST_DATABASE_URL = f"postgresql+asyncpg://{TEST_DB_USER}:{encoded_password}@{TEST_DB_HOST}:{TEST_DB_PORT}/{TEST_DB_NAME}"


# ============================================================================
# 重绑应用侧引擎（asyncpg 跨事件循环复用根修）
#
# pytest-asyncio 为每个测试函数创建独立事件循环，而 repositories.base 的模块级
# 引擎默认带连接池：池中连接在上一个事件循环中创建、被下一个循环签出复用时，
# 违反 asyncpg「单连接同一时刻只允许一个操作」的约束，抛出
# InterfaceError("cannot perform operation: another operation is in progress")
# （经 auth.get_current_user 的用户查询触发，auth.py 记录后转 401/500）。
#
# 处理：在导入 opentask.app（连带全部 service/api 模块）之前，把模块级引擎重绑为
# 指向测试库的 NullPool 引擎——每次会话签出新连接、归还即关闭，天然无跨循环复用。
# 服务模块 `from opentask.repositories.base import SessionCreator` 在此后导入，
# 拿到的即重绑后的 SessionMaker。
# ============================================================================

from opentask.repositories import base as _repo_base

_APP_TEST_ENGINE = create_async_engine(TEST_DATABASE_URL, echo=False, poolclass=NullPool)
_repo_base.engine = _APP_TEST_ENGINE
_repo_base.SessionCreator = async_sessionmaker(
    bind=_APP_TEST_ENGINE, autocommit=False, autoflush=False, expire_on_commit=False
)

# 以下 opentask 导入必须放在引擎重绑之后（导入即冻结 SessionCreator 引用）
from opentask.app import App
from opentask.models.base import DBModel
from opentask.repositories.base import get_session
from opentask.models.user.model import UserModel
from opentask.models.tag.model import Tag, TagGroup  # noqa: F401 — metadata 注册
from opentask.models.issue_display_prefs import IssueDisplayPrefs  # noqa: F401 — metadata 注册
from opentask.models.milestone import Milestone  # noqa: F401 — metadata 注册 E8-S1
from opentask.models.issue_vcs_link import IssueVcsLink  # noqa: F401 — metadata 注册 E11-S1
from opentask.models.issue_link import IssueLink  # noqa: F401 — metadata 注册 E76
from opentask.models.activity_read_cursor import ActivityReadCursor  # noqa: F401 — E52
from opentask.models.cycle import Cycle  # noqa: F401 — metadata 注册
from opentask.models.customer import Customer, CustomerRequest, CustomerRequestIssue, CustomerRequestPublicReply  # noqa: F401 — E22/E63
from opentask.models.custom_field import CustomField, IssueCustomFieldValue  # noqa: F401 — E25
from opentask.models.automation import AutomationRule  # noqa: F401 — E26
from opentask.models.automation import AutomationPendingAction  # noqa: F401 — E38
from opentask.models.workspace_webhook import WorkspaceWebhook, WebhookDeliveryLog  # noqa: F401 — E29
from opentask.models.issue_form import IssueForm  # noqa: F401 — E31
from opentask.models.issue_recurrence import IssueRecurrence  # noqa: F401 — E35
from opentask.models.notification_preference import NotificationPreference  # noqa: F401 — E27
from opentask.models.due_reminder_delivery import DueReminderDelivery  # noqa: F401 — E39
from opentask.models.webhook_alert_delivery import WebhookAlertDelivery  # noqa: F401 — E57
from opentask.models.sla import SlaPolicy, IssueSlaClock  # noqa: F401 — E42
from opentask.models.issue.model import CommentReaction  # noqa: F401 — E27
from opentask.jwt_utils import create_access_token


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
    parser.addoption("--use-sso", action="store_true", default=False,
                     help="use real SSO service (default: use mock)")


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

async def _seed_test_users(engine: AsyncEngine) -> None:
    """幂等播种测试用户（TEST_USERS）到测试库。

    登录链（/api/auth/login、/api/auth/login-local）与 JWT 认证
    （get_current_user 按 username/name 查用户）都依赖库中存在这些用户；
    在 fixture 里创建，不依赖外部 SQL。
    """
    from passlib.context import CryptContext
    from sqlalchemy import select

    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

    session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with session_maker() as session:
        # 用户中心基线（权限点 + 系统角色）：与 main.lifespan 的幂等播种一致。
        # 角色表为空时 RbacService 的存量角色桥接失败 → 数据范围退化为 SELF，
        # 项目/需求等列表接口会被部门过滤为空（ASGITransport 不跑 lifespan，需在此补种）。
        from opentask.services.user_center.seed import seed_user_center
        await seed_user_center(session)

        for login_name, spec in TEST_USERS.items():
            result = await session.execute(
                select(UserModel).where(UserModel.username == login_name)
            )
            if result.scalar_one_or_none() is None:
                session.add(UserModel(
                    name=login_name,
                    username=login_name,
                    password_hash=pwd_context.hash(spec["password"]),
                    role="admin" if spec["is_superuser"] else "developer",
                    status=1,
                    token_version=0,
                ))
        await session.commit()


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
    )

    # 创建所有必要的表（仅一次）
    try:
        async with engine.begin() as conn:
            from opentask.models.base import DBModel
            await conn.run_sync(lambda sync_conn: DBModel.metadata.create_all(sync_conn, checkfirst=True))
            # Additive columns (create_all won't ALTER existing tables)
            from sqlalchemy import text as _sql_text
            await conn.execute(_sql_text(
                "ALTER TABLE IF EXISTS notification_preferences "
                "ADD COLUMN IF NOT EXISTS email_enabled BOOLEAN NOT NULL DEFAULT FALSE"
            ))
            await conn.execute(_sql_text(
                "ALTER TABLE IF EXISTS notification_preferences "
                "ADD COLUMN IF NOT EXISTS due_reminder BOOLEAN NOT NULL DEFAULT TRUE"
            ))
            await conn.execute(_sql_text(
                "ALTER TABLE IF EXISTS notification_preferences "
                "ADD COLUMN IF NOT EXISTS due_reminder_digest BOOLEAN NOT NULL DEFAULT FALSE"
            ))
            await conn.execute(_sql_text(
                "ALTER TABLE IF EXISTS notification_preferences "
                "ADD COLUMN IF NOT EXISTS sla_breached BOOLEAN NOT NULL DEFAULT TRUE"
            ))
            await conn.execute(_sql_text(
                "ALTER TABLE IF EXISTS custom_fields "
                "ADD COLUMN IF NOT EXISTS formula_expr TEXT"
            ))
            await conn.execute(_sql_text(
                "ALTER TABLE IF EXISTS custom_fields "
                "ADD COLUMN IF NOT EXISTS formula_result_type VARCHAR(32)"
            ))
            # E44 webhook delivery reliability
            for _stmt in (
                "ALTER TABLE IF EXISTS webhook_delivery_logs ADD COLUMN IF NOT EXISTS delivery_id VARCHAR(64)",
                "ALTER TABLE IF EXISTS webhook_delivery_logs ADD COLUMN IF NOT EXISTS payload_json JSON",
                "ALTER TABLE IF EXISTS webhook_delivery_logs ADD COLUMN IF NOT EXISTS status VARCHAR(32)",
                "ALTER TABLE IF EXISTS webhook_delivery_logs ADD COLUMN IF NOT EXISTS next_attempt_at TIMESTAMP",
                "ALTER TABLE IF EXISTS webhook_delivery_logs ADD COLUMN IF NOT EXISTS max_attempts INTEGER NOT NULL DEFAULT 5",
            ):
                await conn.execute(_sql_text(_stmt))
            # E45 SLA v2 pause
            for _stmt in (
                "ALTER TABLE IF EXISTS sla_policies ADD COLUMN IF NOT EXISTS pause_statuses JSON NOT NULL DEFAULT '[]'",
                "ALTER TABLE IF EXISTS issue_sla_clocks ADD COLUMN IF NOT EXISTS elapsed_before_pause_minutes INTEGER NOT NULL DEFAULT 0",
                "ALTER TABLE IF EXISTS issue_sla_clocks ADD COLUMN IF NOT EXISTS paused_at TIMESTAMP",
                "ALTER TABLE IF EXISTS issue_sla_clocks ADD COLUMN IF NOT EXISTS segment_started_at TIMESTAMP",
            ):
                await conn.execute(_sql_text(_stmt))
            # E50 workspace business hours
            for _stmt in (
                "ALTER TABLE IF EXISTS workspaces ADD COLUMN IF NOT EXISTS timezone VARCHAR(64)",
                "ALTER TABLE IF EXISTS workspaces ADD COLUMN IF NOT EXISTS business_hours JSON",
            ):
                await conn.execute(_sql_text(_stmt))
            # E56 sla policy calendar overlay
            await conn.execute(_sql_text(
                "ALTER TABLE IF EXISTS sla_policies ADD COLUMN IF NOT EXISTS calendar JSON"
            ))
            # E57 webhook dead-letter alerts
            for _stmt in (
                "ALTER TABLE IF EXISTS workspaces ADD COLUMN IF NOT EXISTS webhook_alert_settings JSON",
                "ALTER TABLE IF EXISTS workspace_webhooks ADD COLUMN IF NOT EXISTS alert_settings JSON",
                "ALTER TABLE IF EXISTS workspace_webhooks ADD COLUMN IF NOT EXISTS paused_reason VARCHAR(64)",
                "ALTER TABLE IF EXISTS notification_preferences ADD COLUMN IF NOT EXISTS webhook_delivery_alert BOOLEAN NOT NULL DEFAULT TRUE",
                "ALTER TABLE IF EXISTS notification_preferences ADD COLUMN IF NOT EXISTS insights_digest BOOLEAN NOT NULL DEFAULT FALSE",
            ):
                await conn.execute(_sql_text(_stmt))
            # E61 insights report visibility
            await conn.execute(_sql_text(
                "ALTER TABLE IF EXISTS insights_saved_reports "
                "ADD COLUMN IF NOT EXISTS visibility VARCHAR(16) NOT NULL DEFAULT 'personal'"
            ))
            # E63 customer request public status
            for _stmt in (
                "ALTER TABLE IF EXISTS customer_requests ADD COLUMN IF NOT EXISTS status_token VARCHAR(64)",
                "ALTER TABLE IF EXISTS customer_requests ADD COLUMN IF NOT EXISTS status_token_enabled BOOLEAN NOT NULL DEFAULT FALSE",
                "ALTER TABLE IF EXISTS customer_requests ADD COLUMN IF NOT EXISTS public_replies_enabled BOOLEAN NOT NULL DEFAULT FALSE",
                """
                CREATE TABLE IF NOT EXISTS customer_request_public_replies (
                    id VARCHAR(36) PRIMARY KEY,
                    request_id VARCHAR(36) NOT NULL REFERENCES customer_requests(id) ON DELETE CASCADE,
                    body TEXT NOT NULL,
                    created_at TIMESTAMP NOT NULL
                )
                """,
                "CREATE INDEX IF NOT EXISTS idx_cr_public_replies_request ON customer_request_public_replies (request_id, created_at)",
                "CREATE UNIQUE INDEX IF NOT EXISTS ix_customer_requests_status_token ON customer_requests (status_token)",
            ):
                await conn.execute(_sql_text(_stmt))
            # E60 search FTS mid — PG tsvector + GIN
            for _tbl, _expr, _idx in (
                (
                    "issues",
                    "to_tsvector('simple', coalesce(title,'') || ' ' || coalesce(issue_code,'') || ' ' || "
                    "coalesce(legacy_issue_code,'') || ' ' || left(coalesce(description,''), 16000))",
                    "ix_issues_search_tsv",
                ),
                (
                    "projects",
                    "to_tsvector('simple', coalesce(name,'') || ' ' || left(coalesce(description,''), 16000))",
                    "ix_projects_search_tsv",
                ),
                (
                    "entity_documents",
                    "to_tsvector('simple', coalesce(title,'') || ' ' || left(coalesce(body_md,''), 16000))",
                    "ix_entity_documents_search_tsv",
                ),
                (
                    "issue_comments",
                    "to_tsvector('simple', left(coalesce(content,''), 16000))",
                    "ix_issue_comments_search_tsv",
                ),
            ):
                await conn.execute(_sql_text(
                    f"ALTER TABLE IF EXISTS {_tbl} ADD COLUMN IF NOT EXISTS search_tsv tsvector "
                    f"GENERATED ALWAYS AS ({_expr}) STORED"
                ))
                await conn.execute(_sql_text(
                    f"CREATE INDEX IF NOT EXISTS {_idx} ON {_tbl} USING GIN (search_tsv)"
                ))
                        # E79 project lead_id (create_all may miss ALTER on existing test DBs)
            await conn.execute(_sql_text(
                "ALTER TABLE IF EXISTS projects ADD COLUMN IF NOT EXISTS lead_id VARCHAR(36)"
            ))
            # E48 timeline_action enum values (no alembic per Q6a)
            for _val in ("sla_paused", "sla_resumed", "link_added", "link_removed", "restored", "parent_changed"):
                await conn.execute(
                    _sql_text(f"ALTER TYPE timeline_action ADD VALUE IF NOT EXISTS '{_val}'")
                )
            print(f"[OK] Test database ({TEST_DB_NAME}) tables created")
    except Exception as e:
        import logging
        logging.error(f"Table creation failed: {e}", exc_info=True)
        raise

    # 播种测试用户（登录链 / JWT 认证依赖）
    await _seed_test_users(engine)

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


@pytest_asyncio.fixture(scope="session")
async def seeded_users(test_engine: AsyncEngine) -> AsyncGenerator[AsyncEngine, None]:
    """确保测试库表结构与种子用户（admin/jiangwei）就绪。

    供只走 HTTP 客户端、不直接使用 test_session 的 API 测试依赖；
    播种逻辑在 test_engine 内完成（幂等）。
    """
    yield test_engine


@pytest.fixture
async def test_client(app, seeded_users) -> AsyncGenerator[AsyncClient, None]:
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
        code=f"TEST-REQ-{datetime.now().strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:8]}",
        title="测试需求",
        description="这是一个测试需求",
        status="draft",
        priority="medium",
        tags=[],  # tags 列 NOT NULL（JSON 类型），缺省会触发约束冲突
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

