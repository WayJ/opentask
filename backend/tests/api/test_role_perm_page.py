"""Phase 5 Task 4 管理端补齐端点测试（SQLite 内存库 + 凭据 monkeypatch）

覆盖：
1. GET /api/roles/{id}/permissions：admin 角色回显全量码、viewer 子集、
   CUSTOM 角色 dept_ids 回显、未登录 401、角色不存在 404；
2. GET /api/auth/dingtalk/config 两态：凭据未配置 enabled=false / appKey=None，
   凭据配置后 enabled=true / appKey 下发（免鉴权可访问）；
3. GET /api/users/me：响应含 dingtalkUserId（未绑定 null / 已绑定回显）。
"""
from types import SimpleNamespace
from uuid import uuid4

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
from opentask.models.user_center import Role, RoleDept
from opentask.repositories.base import get_session
from opentask.services.user_center.permission_defs import PERMISSIONS
from opentask.services.user_center.seed import seed_user_center

_pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")

# 登录链路 + RBAC + 部门归属所需的全部表
TABLES = (
    "user",
    "refresh_token",
    "access_tokens",
    "role",
    "permission",
    "role_permission",
    "user_role",
    "user_dept",
    "department",
    "position",
    "role_dept",
)


@pytest_asyncio.fixture
async def env(monkeypatch):
    """SQLite 内存库 + get_session 覆盖的测试环境（已播种；钉钉凭据默认置空）"""
    engine = create_async_engine("sqlite+aiosqlite://", poolclass=StaticPool)
    tables = [DBModel.metadata.tables[n] for n in TABLES]
    async with engine.begin() as conn:
        await conn.run_sync(lambda m: DBModel.metadata.create_all(m, tables=tables))

    maker = async_sessionmaker(engine, expire_on_commit=False)
    async with maker() as session:
        await seed_user_center(session)

    async def override_session():
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

    monkeypatch.setattr(type(config), "dingtalk_app_key", property(lambda self: ""))
    monkeypatch.setattr(type(config), "dingtalk_app_secret", property(lambda self: ""))

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        yield SimpleNamespace(client=client, maker=maker, monkeypatch=monkeypatch)

    app.dependency_overrides.clear()
    await engine.dispose()


async def _make_user(maker, *, username: str, password: str, role: str = "admin") -> None:
    async with maker() as session:
        session.add(
            UserModel(
                name=f"用户-{username}",
                username=username,
                password_hash=_pwd.hash(password),
                role=role,
            )
        )
        await session.commit()


async def _login_headers(env, username: str, password: str, role: str = "admin") -> dict:
    await _make_user(env.maker, username=username, password=password, role=role)
    resp = await env.client.post(
        "/api/auth/login-local", json={"userName": username, "password": password}
    )
    assert resp.status_code == 200, resp.text
    return {"Authorization": f"Bearer {resp.json()['data']['token']}"}


async def _get_role_id(env, code: str) -> str:
    async with env.maker() as session:
        role = (
            await session.execute(select(Role).where(Role.code == code))
        ).scalar_one()
        return str(role.id)


# ============================================================================
# 1. GET /api/roles/{id}/permissions
# ============================================================================


async def test_role_permissions_admin_full(env):
    """admin 角色回显全量权限码（seed 播全量）；dept_ids 空数组"""
    headers = await _login_headers(env, "rootadmin", "AdminPass123")
    role_id = await _get_role_id(env, "admin")

    resp = await env.client.get(f"/api/roles/{role_id}/permissions", headers=headers)
    assert resp.status_code == 200, resp.text
    data = resp.json()["data"]
    assert set(data["codes"]) == {p["code"] for p in PERMISSIONS}
    assert data["dept_ids"] == []


async def test_role_permissions_viewer_subset_and_custom_depts(env):
    """viewer 回显子集；CUSTOM 角色带 dept_ids；未登录 401；不存在 404"""
    headers = await _login_headers(env, "rootadmin2", "AdminPass123")

    viewer_id = await _get_role_id(env, "viewer")
    resp = await env.client.get(f"/api/roles/{viewer_id}/permissions", headers=headers)
    assert resp.status_code == 200, resp.text
    data = resp.json()["data"]
    assert data["codes"] == sorted(f"{m}:view" for m in ("requirement", "issue", "project", "knowledge", "task"))

    # 建 CUSTOM 角色并写 role_dept → dept_ids 回显
    async with env.maker() as session:
        role = Role(
            code=f"custom-{uuid4().hex[:6]}",
            name="自定义范围角色",
            data_scope="CUSTOM",
        )
        session.add(role)
        await session.flush()
        session.add(RoleDept(role_id=str(role.id), dept_id="dept-1"))
        session.add(RoleDept(role_id=str(role.id), dept_id="dept-2"))
        await session.commit()
        custom_id = str(role.id)

    resp = await env.client.get(f"/api/roles/{custom_id}/permissions", headers=headers)
    assert resp.status_code == 200, resp.text
    data = resp.json()["data"]
    assert sorted(data["dept_ids"]) == ["dept-1", "dept-2"]
    assert data["codes"] == []

    # 未登录被拒（中间件对无 token 请求返回 401/403）
    assert (
        await env.client.get(f"/api/roles/{viewer_id}/permissions")
    ).status_code in (401, 403)
    # 不存在 404
    assert (
        await env.client.get("/api/roles/not-exist/permissions", headers=headers)
    ).status_code == 404


# ============================================================================
# 2. GET /api/auth/dingtalk/config 两态
# ============================================================================


async def test_dingtalk_config_disabled(env):
    """凭据未配置：enabled=false、appKey=None（免鉴权可访问）"""
    resp = await env.client.get("/api/auth/dingtalk/config")
    assert resp.status_code == 200, resp.text
    data = resp.json()["data"]
    assert data == {"enabled": False, "appKey": None}


async def test_dingtalk_config_enabled(env):
    """凭据已配置：enabled=true、appKey 下发（AppSecret 不出后端）"""
    env.monkeypatch.setattr(
        type(config), "dingtalk_app_key", property(lambda self: "ding-app-key")
    )
    env.monkeypatch.setattr(
        type(config), "dingtalk_app_secret", property(lambda self: "ding-secret")
    )
    resp = await env.client.get("/api/auth/dingtalk/config")
    assert resp.status_code == 200, resp.text
    data = resp.json()["data"]
    assert data == {"enabled": True, "appKey": "ding-app-key"}


# ============================================================================
# 3. GET /api/users/me 带 dingtalkUserId
# ============================================================================


async def test_users_me_dingtalk_user_id(env):
    """未绑定 dingtalkUserId=null；已绑定回显钉钉 userid"""
    headers = await _login_headers(env, "me-user", "MyPass1234")

    resp = await env.client.get("/api/users/me", headers=headers)
    assert resp.status_code == 200, resp.text
    assert resp.json()["data"]["dingtalkUserId"] is None

    # 绑定后回显
    async with env.maker() as session:
        user = (
            await session.execute(select(UserModel).where(UserModel.username == "me-user"))
        ).scalar_one()
        user.dingtalk_user_id = "dt-user-001"
        await session.commit()

    resp = await env.client.get("/api/users/me", headers=headers)
    assert resp.status_code == 200, resp.text
    assert resp.json()["data"]["dingtalkUserId"] == "dt-user-001"
