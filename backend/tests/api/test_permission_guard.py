"""require_permission 权限守卫测试（SQLite 内存库旁路 MySQL）

覆盖（Phase 3 Task 2）：
1. viewer：GET /api/users 与 PUT /api/users/{id}/status → 403
2. admin（桥接 role 字符串）：列表/status/role/migrate 四处全放行
3. maintainer（桥接）：列表/status/role 放行、migrate → 403
4. /api/users/me 的 permissions 来自 RbacService 真实计算（viewer 无 manage:*）
5. seed 重跑幂等：新增权限码不影响计数稳定，migrate 码只给 admin
"""
from types import SimpleNamespace

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from passlib.context import CryptContext
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

import opentask.models  # noqa: F401 全量注册（FK 字符串引用需要）
from opentask.app import App
from opentask.config import config
from opentask.models.base import DBModel
from opentask.models.user.model import UserModel
from opentask.models.user_center import Permission, Role, RolePermission
from opentask.repositories.base import get_session
from opentask.services.user_center import permission_defs
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

USERS_URL = "/api/users"
MIGRATE_URL = "/api/user-center/migrate/sso"

# viewer 播种后的权限集（5 个业务模块的 view 码）
VIEWER_PERMS = {
    f"{m}:view" for m in ("requirement", "issue", "project", "knowledge", "task")
}


@pytest_asyncio.fixture
async def guard():
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


async def _make_user(maker, *, username: str, password: str, role: str) -> UserModel:
    """建一个带 bcrypt 哈希的本地用户（role 字符串走 RbacService 桥接路径）"""
    async with maker() as session:
        user = UserModel(
            name=f"用户-{username}",
            username=username,
            password_hash=_pwd.hash(password),
            role=role,
        )
        session.add(user)
        await session.commit()
        found = (
            await session.execute(select(UserModel).where(UserModel.username == username))
        ).scalar_one()
        return found


async def _login_headers(guard, *, username: str, password: str, role: str) -> dict:
    """建用户（桥接 role 字符串）→ login-local 登录 → Authorization 头"""
    await _make_user(guard.maker, username=username, password=password, role=role)
    resp = await guard.client.post(
        "/api/auth/login-local", json={"userName": username, "password": password}
    )
    assert resp.status_code == 200, resp.text
    return {"Authorization": f"Bearer {resp.json()['data']['token']}"}


async def _role_perm_codes(maker, role_code: str) -> set[str]:
    """查询某角色的权限码集合"""
    async with maker() as session:
        result = await session.execute(
            select(Permission.code)
            .join(RolePermission, RolePermission.permission_id == Permission.id)
            .join(Role, Role.id == RolePermission.role_id)
            .where(Role.code == role_code)
        )
        return set(result.scalars().all())


# ============================================================================
# 1. viewer → 403
# ============================================================================

async def test_viewer_forbidden(guard):
    """viewer：GET /api/users → 403；PUT status → 403，均为「权限不足」"""
    headers = await _login_headers(
        guard, username="viewer1", password="ViewerPass123", role="viewer"
    )

    resp = await guard.client.get(USERS_URL, headers=headers)
    assert resp.status_code == 403
    assert "权限不足" in resp.json()["detail"]

    target = await _make_user(
        guard.maker, username="dev_target", password="DevPass1234", role="developer"
    )
    resp = await guard.client.put(
        f"{USERS_URL}/{target.id}/status", json={"status": 0}, headers=headers
    )
    assert resp.status_code == 403
    assert "权限不足" in resp.json()["detail"]


# ============================================================================
# 2. admin 四处全放行
# ============================================================================

async def test_admin_all_allowed(guard, monkeypatch):
    """admin（桥接 role 字符串）：列表/status/role/migrate 全放行"""
    monkeypatch.setattr(type(config), "sso_enabled", property(lambda self: True))
    headers = await _login_headers(
        guard, username="admin1", password="AdminPass123", role="admin"
    )
    target = await _make_user(
        guard.maker, username="dev_target", password="DevPass1234", role="developer"
    )

    # GET /api/users（menu:manage_user）
    resp = await guard.client.get(USERS_URL, headers=headers)
    assert resp.status_code == 200, resp.text

    # PUT status（manage:user:status）
    resp = await guard.client.put(
        f"{USERS_URL}/{target.id}/status", json={"status": 0}, headers=headers
    )
    assert resp.status_code == 200, resp.text

    # PUT role（manage:user:role，目标非 admin 且非本人）
    resp = await guard.client.put(
        f"{USERS_URL}/{target.id}/role", json={"role": "viewer"}, headers=headers
    )
    assert resp.status_code == 200, resp.text

    # POST migrate（manage:user:migrate）
    resp = await guard.client.post(MIGRATE_URL, headers=headers)
    assert resp.status_code == 200, resp.text


# ============================================================================
# 3. maintainer：status/role/列表放行、migrate 403
# ============================================================================

async def test_maintainer_partial_allowed(guard, monkeypatch):
    """maintainer：列表/status/role 放行；migrate（admin 专属码）→ 403"""
    monkeypatch.setattr(type(config), "sso_enabled", property(lambda self: True))
    headers = await _login_headers(
        guard, username="maint1", password="MaintPass123", role="maintainer"
    )
    target = await _make_user(
        guard.maker, username="dev_target", password="DevPass1234", role="developer"
    )

    resp = await guard.client.get(USERS_URL, headers=headers)
    assert resp.status_code == 200, resp.text

    resp = await guard.client.put(
        f"{USERS_URL}/{target.id}/status", json={"status": 0}, headers=headers
    )
    assert resp.status_code == 200, resp.text

    resp = await guard.client.put(
        f"{USERS_URL}/{target.id}/role", json={"role": "viewer"}, headers=headers
    )
    assert resp.status_code == 200, resp.text

    # migrate 权限码只给 admin
    resp = await guard.client.post(MIGRATE_URL, headers=headers)
    assert resp.status_code == 403
    assert "权限不足" in resp.json()["detail"]


# ============================================================================
# 4. /api/users/me 的 permissions 来自 RbacService
# ============================================================================

async def test_me_permissions_from_rbac(guard):
    """/api/users/me 返回 RbacService 计算的真实权限集：viewer 无 manage:*/menu:*"""
    headers = await _login_headers(
        guard, username="viewer2", password="ViewerPass123", role="viewer"
    )

    resp = await guard.client.get(f"{USERS_URL}/me", headers=headers)
    assert resp.status_code == 200, resp.text
    permissions = resp.json()["data"]["permissions"]

    assert permissions == sorted(VIEWER_PERMS)
    assert not any(p.startswith(("manage:", "menu:")) for p in permissions)


# ============================================================================
# 5. 重播种幂等 + migrate 码归属
# ============================================================================

async def test_reseed_idempotent_with_migrate_code(guard):
    """跑 seed 两遍：计数与 role_permission 均稳定；migrate 码只在 admin"""
    async with guard.maker() as session:
        first = await seed_user_center(session)
        rp_first = len((await session.execute(select(RolePermission))).all())

        second = await seed_user_center(session)
        rp_second = len((await session.execute(select(RolePermission))).all())

    assert second == first
    assert first["permissions"] == len(permission_defs.PERMISSIONS)
    assert rp_second == rp_first

    admin_codes = await _role_perm_codes(guard.maker, "admin")
    maintainer_codes = await _role_perm_codes(guard.maker, "maintainer")
    viewer_codes = await _role_perm_codes(guard.maker, "viewer")
    assert "manage:user:migrate" in admin_codes
    assert "manage:user:migrate" not in maintainer_codes
    assert "manage:user:migrate" not in viewer_codes

    # permission 表计数与字典一致（新码已入库）
    async with guard.maker() as session:
        perm_count = (
            await session.execute(select(func.count()).select_from(Permission))
        ).scalar_one()
    assert perm_count == len(permission_defs.PERMISSIONS)
