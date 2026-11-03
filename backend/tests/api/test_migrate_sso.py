"""SSO 存量用户迁移命令测试（SQLite 内存库旁路 MySQL）

覆盖（Phase 2 Task 3，Phase 3 Task 2 改为权限码门槛）：
1. admin + sso_enabled=true：3 个无密码用户迁移，CSV 含 3 行，
   临时密码可走 /api/auth/login 登录且 mustChangePassword=true
2. 幂等：重跑 migrated=0，CSV 为空
3. 无 manage:user:migrate 权限 → 403（权限不足）
4. sso_enabled=false → 403（需开启 SSO 兼容模式）
5. username 回填唯一化：重名用户得到不同 username
"""
import csv
import io
from types import SimpleNamespace

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

import opentask.models  # noqa: F401 全量注册（FK 字符串引用需要）
from opentask.app import App
from opentask.config import config
from opentask.models.base import DBModel
from opentask.models.user.model import UserModel
from opentask.repositories.base import get_session
from opentask.services.user_center.seed import seed_user_center

# 密码哈希上下文（bcrypt），与 auth_service 保持一致
_pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")

# 登录链路表 + 权限门槛（require_permission → RbacService）所需表
TABLES = (
    "user",
    "refresh_token",
    "access_tokens",
    "role",
    "permission",
    "role_permission",
    "user_role",
)

MIGRATE_URL = "/api/user-center/migrate/sso"


@pytest_asyncio.fixture
async def mig():
    """SQLite 内存库 + dependency_overrides[get_session] 旁路 MySQL 的测试环境"""
    engine = create_async_engine("sqlite+aiosqlite://", poolclass=StaticPool)
    tables = [DBModel.metadata.tables[n] for n in TABLES]
    async with engine.begin() as conn:
        await conn.run_sync(lambda m: DBModel.metadata.create_all(m, tables=tables))

    maker = async_sessionmaker(engine, expire_on_commit=False)

    # 播种系统角色与权限点（require_permission 权限门槛的数据来源）
    async with maker() as session:
        await seed_user_center(session)

    async def override_session():
        """与 repositories.base.get_session 相同的提交/回滚语义"""
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
    app.dependency_overrides[get_session] = override_session

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        yield SimpleNamespace(client=client, maker=maker)

    app.dependency_overrides.clear()
    await engine.dispose()


async def _make_user(maker, *, username=None, password=None, **kwargs) -> UserModel:
    """建用户：password 传入时 bcrypt 哈希落库，不传即"从未设过本地密码"的存量用户"""
    async with maker() as session:
        user = UserModel(
            name=kwargs.pop("name", None),
            username=username,
            password_hash=_pwd.hash(password) if password else None,
            **kwargs,
        )
        session.add(user)
        await session.commit()
        found = (
            await session.execute(select(UserModel).where(UserModel.id == user.id))
        ).scalar_one()
        return found


async def _login_token(client, maker, *, username, password, role=None) -> str:
    """建用户 → login-local 登录 → 返回 access token（不依赖 SSO 开关）"""
    kwargs = {"role": role} if role else {}
    await _make_user(maker, username=username, password=password, **kwargs)
    resp = await client.post(
        "/api/auth/login-local", json={"userName": username, "password": password}
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["data"]["token"]


def _parse_csv(csv_text: str) -> list[tuple[str, str]]:
    """解析响应 CSV：校验表头并跳过，返回 [(username, temp_password), ...]"""
    reader = csv.reader(io.StringIO(csv_text))
    header = next(reader, None)
    assert header == ["username", "temp_password"]
    return [(row[0], row[1]) for row in reader]


async def _prepare_env(mig, monkeypatch):
    """开启 SSO 兼容模式并返回 admin 请求头"""
    monkeypatch.setattr(type(config), "sso_enabled", property(lambda self: True))
    token = await _login_token(
        mig.client, mig.maker,
        username="admin", password="AdminPass123", role="admin",
    )
    return {"Authorization": f"Bearer {token}"}


async def _seed_legacy_users(maker) -> None:
    """造 3 个无密码存量用户 + 1 个已有 password_hash 的用户

    - sso_a：有 sso_account（回填 username 应取 sso_account）
    - legacy1 / legacy2：只有 name 且重名（唯一化应得到不同 username）
    - local_user：已有 password_hash（应跳过）
    """
    await _make_user(maker, name="用户A", sso_account="sso_a")
    await _make_user(maker, name="wang")
    await _make_user(maker, name="wang")
    await _make_user(maker, username="local_user", password="LocalPass123")


# ============================================================================
# 1+5. 迁移成功 + username 唯一化 + 临时密码可登录
# ============================================================================

async def test_migrate_success_and_login_with_temp_password(mig, monkeypatch):
    """admin + sso_enabled=true → migrated=3；CSV 3 行；临时密码走 /api/auth/login 可登录"""
    headers = await _prepare_env(mig, monkeypatch)
    await _seed_legacy_users(mig.maker)

    resp = await mig.client.post(MIGRATE_URL, headers=headers)
    assert resp.status_code == 200, resp.text
    data = resp.json()["data"]
    assert data["migrated"] == 3

    rows = _parse_csv(data["csv"])
    assert len(rows) == 3
    usernames = [u for u, _ in rows]
    # username 回填：sso_account 优先
    assert "sso_a" in usernames
    # local_user 已有密码，不在迁移名单
    assert "local_user" not in usernames

    # 抽一个实际走 /api/auth/login 验证临时密码（切回本地登录路径）
    monkeypatch.setattr(type(config), "sso_enabled", property(lambda self: False))
    target, temp_password = rows[0]
    login = await mig.client.post(
        "/api/auth/login", json={"userName": target, "password": temp_password}
    )
    assert login.status_code == 200, login.text
    assert login.json()["data"]["mustChangePassword"] is True

    # 库内校验：must_change_password 已置位、password_hash 非空且非明文
    async with mig.maker() as session:
        user = (
            await session.execute(select(UserModel).where(UserModel.username == target))
        ).scalar_one()
        assert user.must_change_password is True
        assert user.password_hash and user.password_hash != temp_password

        # 已有密码的用户未被改动
        local = (
            await session.execute(
                select(UserModel).where(UserModel.username == "local_user")
            )
        ).scalar_one()
        assert local.must_change_password is False
        assert _pwd.verify("LocalPass123", local.password_hash)


# ============================================================================
# 5. username 回填唯一化
# ============================================================================

async def test_migrate_username_backfill_unique(mig, monkeypatch):
    """重名用户得到不同 username（lower 归一化判重，与 Phase 1 迁移一致）"""
    headers = await _prepare_env(mig, monkeypatch)
    await _seed_legacy_users(mig.maker)

    resp = await mig.client.post(MIGRATE_URL, headers=headers)
    rows = _parse_csv(resp.json()["data"]["csv"])
    usernames = [u for u, _ in rows]

    # 只有 name 的两个重名 wang：一个 wang、一个 wang_2，互不相同
    wangs = sorted(u for u in usernames if u.startswith("wang"))
    assert len(wangs) == 2
    assert wangs == ["wang", "wang_2"]
    # 全量 username 无重复
    assert len(set(u.lower() for u in usernames)) == len(usernames)


# ============================================================================
# 1b. 钉钉用户不迁移（J4）
# ============================================================================

async def test_migrate_excludes_dingtalk_users(mig, monkeypatch):
    """password_hash 为空但 dingtalk_user_id 非空的用户不迁移

    钉钉同步/免登用户走钉钉通道，无本地密码语义，不生成临时密码。
    """
    headers = await _prepare_env(mig, monkeypatch)
    # 普通无密码存量用户 + 钉钉用户（password_hash=None + dingtalk_user_id 非空）
    await _make_user(mig.maker, name="存量无密")
    await _make_user(mig.maker, name="钉钉用户", dingtalk_user_id="dt_001")

    resp = await mig.client.post(MIGRATE_URL, headers=headers)
    assert resp.status_code == 200, resp.text
    data = resp.json()["data"]
    assert data["migrated"] == 1  # 只有存量无密用户

    rows = _parse_csv(data["csv"])
    assert len(rows) == 1

    # 钉钉用户未被改动：无临时密码、不强制改密
    async with mig.maker() as session:
        ding = (
            await session.execute(
                select(UserModel).where(UserModel.dingtalk_user_id == "dt_001")
            )
        ).scalar_one()
        assert ding.password_hash is None
        assert ding.must_change_password is False
        assert ding.username is None  # 未回填 username


# ============================================================================
# 2. 幂等：重跑 migrated=0
# ============================================================================

async def test_migrate_idempotent_rerun(mig, monkeypatch):
    """重跑 → migrated=0，CSV 为空"""
    headers = await _prepare_env(mig, monkeypatch)
    await _seed_legacy_users(mig.maker)

    first = await mig.client.post(MIGRATE_URL, headers=headers)
    assert first.json()["data"]["migrated"] == 3

    second = await mig.client.post(MIGRATE_URL, headers=headers)
    assert second.status_code == 200
    data = second.json()["data"]
    assert data["migrated"] == 0
    assert data["csv"] == ""


# ============================================================================
# 3. 无权限 → 403
# ============================================================================

async def test_migrate_forbidden_for_non_admin(mig, monkeypatch):
    """viewer 角色调用 → 403，错误信息为「权限不足」（无 manage:user:migrate）"""
    monkeypatch.setattr(type(config), "sso_enabled", property(lambda self: True))
    token = await _login_token(
        mig.client, mig.maker,
        username="viewer1", password="ViewerPass123", role="viewer",
    )

    resp = await mig.client.post(
        MIGRATE_URL, headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == 403
    assert "权限不足" in resp.json()["detail"]


# ============================================================================
# 4. sso_enabled=false → 403
# ============================================================================

async def test_migrate_forbidden_when_sso_disabled(mig, monkeypatch):
    """sso_enabled=false 时 admin 调用 → 403，错误信息为"需开启 SSO 兼容模式" """
    monkeypatch.setattr(type(config), "sso_enabled", property(lambda self: False))
    token = await _login_token(
        mig.client, mig.maker,
        username="admin", password="AdminPass123", role="admin",
    )

    resp = await mig.client.post(
        MIGRATE_URL, headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == 403
    assert "SSO 兼容模式" in resp.json()["detail"]
