"""管理端 CRUD 测试（Phase 5 Task 1）：角色 / 权限点 / 用户（SQLite 内存库旁路 MySQL）

覆盖：
1. 角色 CRUD 全路径：创建（code 唯一 409 / 非法 data_scope 400）、更新
   （系统角色只许改 name/description、CUSTOM + dept_ids 覆盖 role_dept）、
   删除（系统角色 409、关联用户 409）、权限整组覆盖（不存在/停用码 400、admin 409）；
2. 权限点启停 → require_permission 行为变化（停用 manage:user:status 后 maintainer 403，
   重新启用恢复）；
3. 用户建号：密码空（无 hash + must_change_password）、带密码（可直接登录）、
   username 唯一（大小写不敏感 409）、角色桥接双写（user_role 行 + role 字符串）；
4. 用户编辑（name/role_codes 双写；username 不可改）；
5. 软删（旧 token 因 token_version+1 立即 401；重复删 409）；
6. 重置密码（明文临时密码只返一次、旧 token 失效、临时密码可登录 + mustChangePassword）；
7. 用户列表 dept_id / role（user_role join + 存量字符串回退）筛选。
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
from opentask.models.base import DBModel
from opentask.models.user.model import UserModel
from opentask.models.user_center import (
    Department,
    Permission,
    Role,
    RoleDept,
    RolePermission,
    UserDept,
    UserRole,
)
from opentask.repositories.base import get_session
from opentask.services.user_center.seed import seed_user_center

# 密码哈希上下文（bcrypt），与 auth_service 保持一致
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

USERS_URL = "/api/users"
ROLES_URL = "/api/roles"
PERMS_URL = "/api/permissions"


@pytest_asyncio.fixture
async def admin():
    """SQLite 内存库 + dependency_overrides[get_session] 旁路 MySQL 的测试环境（已播种）"""
    engine = create_async_engine("sqlite+aiosqlite://", poolclass=StaticPool)
    tables = [DBModel.metadata.tables[n] for n in TABLES]
    async with engine.begin() as conn:
        await conn.run_sync(lambda m: DBModel.metadata.create_all(m, tables=tables))

    maker = async_sessionmaker(engine, expire_on_commit=False)

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


async def _make_user(maker, *, username: str, password: str | None = None, role: str = "viewer", **kwargs) -> UserModel:
    """直插一个本地用户（password None = 无 hash；role 走存量字符串桥接）"""
    async with maker() as session:
        user = UserModel(
            name=f"用户-{username}",
            username=username,
            password_hash=_pwd.hash(password) if password else None,
            role=role,
            **kwargs,
        )
        session.add(user)
        await session.commit()
        found = (
            await session.execute(select(UserModel).where(UserModel.username == username))
        ).scalar_one()
        return found


async def _login_headers(admin_fixture, *, username: str, password: str, role: str) -> dict:
    """建用户（role 字符串桥接）→ login-local 登录 → Authorization 头"""
    await _make_user(admin_fixture.maker, username=username, password=password, role=role)
    resp = await admin_fixture.client.post(
        "/api/auth/login-local", json={"userName": username, "password": password}
    )
    assert resp.status_code == 200, resp.text
    return {"Authorization": f"Bearer {resp.json()['data']['token']}"}


async def _admin_headers(admin_fixture) -> dict:
    """admin（桥接 role 字符串，seed 后持有全量权限码）登录头"""
    return await _login_headers(
        admin_fixture, username="rootadmin", password="AdminPass123", role="admin"
    )


async def _get_role(admin_fixture, code: str) -> Role:
    async with admin_fixture.maker() as session:  # type: ignore[attr-defined]
        return (
            await session.execute(select(Role).where(Role.code == code))
        ).scalar_one()


async def _get_perm(admin_fixture, code: str) -> Permission:
    async with admin_fixture.maker() as session:  # type: ignore[attr-defined]
        return (
            await session.execute(select(Permission).where(Permission.code == code))
        ).scalar_one()


async def _make_dept(admin_fixture, name: str = "研发部") -> Department:
    async with admin_fixture.maker() as session:  # type: ignore[attr-defined]
        dept = Department(name=name, path=f"/{uuid4().hex[:8]}")
        session.add(dept)
        await session.commit()
        found = (
            await session.execute(select(Department).where(Department.name == name))
        ).scalar_one()
        return found


# ============================================================================
# 1. 角色 CRUD
# ============================================================================

async def test_roles_list_compat_shape(admin):
    """GET /api/roles：登录即可；data 兼容旧结构 value/label/description + 新字段"""
    headers = await _login_headers(
        admin, username="viewer_roles", password="ViewerPass123", role="viewer"
    )
    resp = await admin.client.get(ROLES_URL, headers=headers)
    assert resp.status_code == 200, resp.text
    data = resp.json()["data"]
    by_code = {r["value"]: r for r in data}
    assert {"admin", "maintainer", "developer", "viewer"} <= set(by_code)
    admin_role = by_code["admin"]
    assert admin_role["label"] == "系统管理员"
    assert admin_role["is_system"] is True
    assert admin_role["data_scope"] == "ALL"
    assert "id" in admin_role


async def test_role_create_update_delete(admin):
    """角色全生命周期：创建 → 更新（CUSTOM + dept_ids）→ 删除"""
    headers = await _admin_headers(admin)

    # 创建
    resp = await admin.client.post(
        ROLES_URL,
        json={"code": "auditor", "name": "审计员", "data_scope": "DEPT"},
        headers=headers,
    )
    assert resp.status_code == 200, resp.text
    role_id = resp.json()["data"]["id"]

    # code 唯一 → 409
    resp = await admin.client.post(
        ROLES_URL, json={"code": "auditor", "name": "重复"}, headers=headers
    )
    assert resp.status_code == 409

    # 大小写变体同样 409（MySQL ci collation 唯一索引不区分大小写，
    # 精确等值判重会被 "AUDITOR" 绕过、撞唯一索引变 500）
    resp = await admin.client.post(
        ROLES_URL, json={"code": "AUDITOR", "name": "大写重复"}, headers=headers
    )
    assert resp.status_code == 409

    # 系统角色的大写变体同样拦截
    resp = await admin.client.post(
        ROLES_URL, json={"code": "Admin", "name": "仿系统角色"}, headers=headers
    )
    assert resp.status_code == 409

    # 非法 data_scope → 400
    resp = await admin.client.post(
        ROLES_URL, json={"code": "bad", "name": "坏档位", "data_scope": "GALAXY"}, headers=headers
    )
    assert resp.status_code == 400

    # 更新为 CUSTOM + dept_ids 覆盖 role_dept
    dept = await _make_dept(admin, "审计范围部门")
    resp = await admin.client.put(
        f"{ROLES_URL}/{role_id}",
        json={"name": "审计员2", "data_scope": "CUSTOM", "dept_ids": [str(dept.id)]},
        headers=headers,
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["data"]["data_scope"] == "CUSTOM"
    async with admin.maker() as session:
        rows = list(
            (
                await session.execute(select(RoleDept).where(RoleDept.role_id == role_id))
            ).scalars().all()
        )
    assert [r.dept_id for r in rows] == [str(dept.id)]

    # 无用户挂载 → 可删除
    resp = await admin.client.delete(f"{ROLES_URL}/{role_id}", headers=headers)
    assert resp.status_code == 200, resp.text
    resp = await admin.client.get(ROLES_URL, headers=headers)
    assert "auditor" not in {r["value"] for r in resp.json()["data"]}


async def test_role_update_system_protection(admin):
    """系统角色只许改 name/description；data_scope / dept_ids → 400"""
    headers = await _admin_headers(admin)
    admin_role = await _get_role(admin, "admin")

    resp = await admin.client.put(
        f"{ROLES_URL}/{admin_role.id}", json={"name": "超管"}, headers=headers
    )
    assert resp.status_code == 200, resp.text

    resp = await admin.client.put(
        f"{ROLES_URL}/{admin_role.id}", json={"data_scope": "SELF"}, headers=headers
    )
    assert resp.status_code == 400

    resp = await admin.client.put(
        f"{ROLES_URL}/{admin_role.id}", json={"dept_ids": [uuid4().hex]}, headers=headers
    )
    assert resp.status_code == 400


async def test_role_delete_protection(admin):
    """删除保护：系统角色 409；有关联用户 409"""
    headers = await _admin_headers(admin)

    admin_role = await _get_role(admin, "admin")
    resp = await admin.client.delete(f"{ROLES_URL}/{admin_role.id}", headers=headers)
    assert resp.status_code == 409

    # 造一个带用户的自定义角色
    resp = await admin.client.post(
        ROLES_URL, json={"code": "temp-role", "name": "临时角色"}, headers=headers
    )
    assert resp.status_code == 200, resp.text
    role_id = resp.json()["data"]["id"]
    user = await _make_user(admin.maker, username="bound_user", password="Passw0rd123")
    async with admin.maker() as session:
        session.add(UserRole(user_id=str(user.id), role_id=role_id))
        await session.commit()

    resp = await admin.client.delete(f"{ROLES_URL}/{role_id}", headers=headers)
    assert resp.status_code == 409


async def test_role_permissions_overwrite(admin):
    """权限整组覆盖：正常覆盖、不存在码 400、停用码 400、admin 角色 409"""
    headers = await _admin_headers(admin)

    resp = await admin.client.post(
        ROLES_URL, json={"code": "perm-role", "name": "权限测试角色"}, headers=headers
    )
    assert resp.status_code == 200, resp.text
    role_id = resp.json()["data"]["id"]

    # 覆盖为一组权限
    codes = ["requirement:view", "issue:view"]
    resp = await admin.client.put(
        f"{ROLES_URL}/{role_id}/permissions", json={"codes": codes}, headers=headers
    )
    assert resp.status_code == 200, resp.text
    async with admin.maker() as session:
        got = {
            c
            for c in (
                await session.execute(
                    select(Permission.code)
                    .join(RolePermission, RolePermission.permission_id == Permission.id)
                    .where(RolePermission.role_id == role_id)
                )
            ).scalars().all()
        }
    assert got == set(codes)

    # 再覆盖为另一组（验证整组替换而非追加）
    resp = await admin.client.put(
        f"{ROLES_URL}/{role_id}/permissions", json={"codes": ["project:view"]}, headers=headers
    )
    assert resp.status_code == 200, resp.text
    async with admin.maker() as session:
        got = {
            c
            for c in (
                await session.execute(
                    select(Permission.code)
                    .join(RolePermission, RolePermission.permission_id == Permission.id)
                    .where(RolePermission.role_id == role_id)
                )
            ).scalars().all()
        }
    assert got == {"project:view"}

    # 不存在的码 → 400
    resp = await admin.client.put(
        f"{ROLES_URL}/{role_id}/permissions", json={"codes": ["nope:view"]}, headers=headers
    )
    assert resp.status_code == 400

    # 停用的码 → 400
    perm = await _get_perm(admin, "manage:user:reset_password")
    resp = await admin.client.put(
        f"{PERMS_URL}/{perm.id}/status", json={"status": 0}, headers=headers
    )
    assert resp.status_code == 200, resp.text
    resp = await admin.client.put(
        f"{ROLES_URL}/{role_id}/permissions",
        json={"codes": ["manage:user:reset_password"]},
        headers=headers,
    )
    assert resp.status_code == 400
    # 恢复启用，避免影响后续用例
    resp = await admin.client.put(
        f"{PERMS_URL}/{perm.id}/status", json={"status": 1}, headers=headers
    )
    assert resp.status_code == 200

    # admin 角色 → 409
    admin_role = await _get_role(admin, "admin")
    resp = await admin.client.put(
        f"{ROLES_URL}/{admin_role.id}/permissions", json={"codes": []}, headers=headers
    )
    assert resp.status_code == 409


async def test_role_write_requires_permission(admin):
    """viewer（无 manage:role:*）创建角色 → 403；GET 列表登录即可"""
    viewer_headers = await _login_headers(
        admin, username="viewer_role2", password="ViewerPass123", role="viewer"
    )
    resp = await admin.client.post(
        ROLES_URL, json={"code": "sneak", "name": "偷建"}, headers=viewer_headers
    )
    assert resp.status_code == 403


# ============================================================================
# 2. 权限点启停 → require_permission 行为变化
# ============================================================================

async def test_permission_toggle_changes_guard(admin):
    """停用 manage:user:status → maintainer 由放行变 403；重新启用恢复"""
    admin_headers = await _admin_headers(admin)
    maintainer_headers = await _login_headers(
        admin, username="maint_toggle", password="MaintPass123", role="maintainer"
    )
    target = await _make_user(
        admin.maker, username="toggle_target", password="Passw0rd123", role="developer"
    )

    # maintainer 初始有 manage:user:status（seed）→ 放行
    resp = await admin.client.put(
        f"{USERS_URL}/{target.id}/status", json={"status": 0}, headers=maintainer_headers
    )
    assert resp.status_code == 200, resp.text
    # 恢复目标状态
    resp = await admin.client.put(
        f"{USERS_URL}/{target.id}/status", json={"status": 1}, headers=maintainer_headers
    )
    assert resp.status_code == 200, resp.text

    # 停用权限点
    perm = await _get_perm(admin, "manage:user:status")
    resp = await admin.client.put(
        f"{PERMS_URL}/{perm.id}/status", json={"status": 0}, headers=admin_headers
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["data"]["status"] == 0

    # 同一个 maintainer 立即 403
    resp = await admin.client.put(
        f"{USERS_URL}/{target.id}/status", json={"status": 0}, headers=maintainer_headers
    )
    assert resp.status_code == 403
    assert "权限不足" in resp.json()["detail"]

    # 重新启用 → 恢复
    resp = await admin.client.put(
        f"{PERMS_URL}/{perm.id}/status", json={"status": 1}, headers=admin_headers
    )
    assert resp.status_code == 200
    resp = await admin.client.put(
        f"{USERS_URL}/{target.id}/status", json={"status": 1}, headers=maintainer_headers
    )
    assert resp.status_code == 200, resp.text


# ============================================================================
# 3. 用户建号
# ============================================================================

async def test_create_user_without_password(admin):
    """密码空 → 无 hash + must_change_password=True；双写 user_role + role 字符串"""
    headers = await _admin_headers(admin)
    resp = await admin.client.post(
        USERS_URL,
        json={"username": "nopass", "name": "无密码", "role_codes": ["developer", "viewer"]},
        headers=headers,
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()["data"]
    assert data["must_change_password"] is True

    user_id = data["id"]
    async with admin.maker() as session:
        user = (
            await session.execute(select(UserModel).where(UserModel.id == user_id))
        ).scalar_one()
        assert user.password_hash is None
        assert user.must_change_password is True
        # 桥接双写：role 字符串 = 第一个角色 code
        assert user.role == "developer"
        role_codes = [
            c
            for c in (
                await session.execute(
                    select(Role.code)
                    .join(UserRole, UserRole.role_id == Role.id)
                    .where(UserRole.user_id == user_id)
                )
            ).scalars().all()
        ]
    assert sorted(role_codes) == ["developer", "viewer"]

    # 无 hash 用户不能本地登录
    resp = await admin.client.post(
        "/api/auth/login-local", json={"userName": "nopass", "password": "whatever123"}
    )
    assert resp.status_code == 401


async def test_create_user_with_password_and_depts(admin):
    """带密码 + 部门归属 → 可登录；user_dept 行落库"""
    headers = await _admin_headers(admin)
    dept = await _make_dept(admin, "研发一部")

    resp = await admin.client.post(
        USERS_URL,
        json={
            "username": "withpass",
            "name": "带密码",
            "role_codes": ["maintainer"],
            "password": "InitPass1234",
            "dept_assignments": [{"dept_id": str(dept.id), "is_primary": True}],
        },
        headers=headers,
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()["data"]
    assert data["must_change_password"] is False

    async with admin.maker() as session:
        rows = list(
            (
                await session.execute(
                    select(UserDept).where(UserDept.user_id == data["id"])
                )
            ).scalars().all()
        )
    assert len(rows) == 1
    assert rows[0].dept_id == str(dept.id)
    assert rows[0].is_primary is True

    # 可直接本地登录（密码可用）
    resp = await admin.client.post(
        "/api/auth/login-local", json={"userName": "withpass", "password": "InitPass1234"}
    )
    assert resp.status_code == 200, resp.text


async def test_create_user_validations(admin):
    """username 唯一（大小写不敏感 409）、角色不存在 400、双主部门 400"""
    headers = await _admin_headers(admin)
    await _make_user(admin.maker, username="existing", password="Passw0rd123")

    # 大小写不敏感重名 → 409
    resp = await admin.client.post(
        USERS_URL,
        json={"username": "EXISTING", "name": "重名", "role_codes": []},
        headers=headers,
    )
    assert resp.status_code == 409

    # 角色不存在 → 400
    resp = await admin.client.post(
        USERS_URL,
        json={"username": "badrole", "name": "坏角色", "role_codes": ["ghost"]},
        headers=headers,
    )
    assert resp.status_code == 400

    # 双主部门 → 400
    dept = await _make_dept(admin, "双主部门")
    resp = await admin.client.post(
        USERS_URL,
        json={
            "username": "twoprimary",
            "name": "双主部门",
            "role_codes": [],
            "dept_assignments": [
                {"dept_id": str(dept.id), "is_primary": True},
                {"dept_id": str(dept.id), "is_primary": False},
            ],
        },
        headers=headers,
    )
    assert resp.status_code == 400


# ============================================================================
# 4. 用户编辑
# ============================================================================

async def test_update_user_dual_write(admin):
    """编辑 name/role_codes → 双写；username 不接受修改"""
    headers = await _admin_headers(admin)
    resp = await admin.client.post(
        USERS_URL,
        json={"username": "editable", "name": "待编辑", "role_codes": ["viewer"]},
        headers=headers,
    )
    user_id = resp.json()["data"]["id"]

    resp = await admin.client.put(
        f"{USERS_URL}/{user_id}",
        json={"name": "已编辑", "role_codes": ["developer"], "username": "hacked"},
        headers=headers,
    )
    assert resp.status_code == 200, resp.text

    async with admin.maker() as session:
        user = (
            await session.execute(select(UserModel).where(UserModel.id == user_id))
        ).scalar_one()
        assert user.name == "已编辑"
        # username 是唯一标识，schema 不接受修改
        assert user.username == "editable"
        # 双写：role 字符串 + user_role 行
        assert user.role == "developer"
        codes = [
            c
            for c in (
                await session.execute(
                    select(Role.code)
                    .join(UserRole, UserRole.role_id == Role.id)
                    .where(UserRole.user_id == user_id)
                )
            ).scalars().all()
        ]
    assert codes == ["developer"]


async def test_clear_roles_revokes_bridge(admin):
    """清空角色（role_codes=[]）：user_role 行与 role 字符串同步清空，
    桥接回退不再按旧字符串授权（require_permission 403、getUserInfo roles 为空）"""
    headers = await _admin_headers(admin)
    resp = await admin.client.post(
        USERS_URL,
        json={
            "username": "clearme",
            "name": "待清空",
            "role_codes": ["maintainer"],
            "password": "Passw0rd123",
        },
        headers=headers,
    )
    assert resp.status_code == 200, resp.text
    user_id = resp.json()["data"]["id"]

    login = await admin.client.post(
        "/api/auth/login-local", json={"userName": "clearme", "password": "Passw0rd123"}
    )
    user_headers = {"Authorization": f"Bearer {login.json()['data']['token']}"}

    # maintainer 初始有 menu:manage_user → 列表放行
    resp = await admin.client.get(USERS_URL, headers=user_headers)
    assert resp.status_code == 200, resp.text

    # 管理员清空角色
    resp = await admin.client.put(
        f"{USERS_URL}/{user_id}", json={"role_codes": []}, headers=headers
    )
    assert resp.status_code == 200, resp.text

    # 同一 token 立即 403（无 user_role 行 + role 空串 → 无角色无权限）
    resp = await admin.client.get(USERS_URL, headers=user_headers)
    assert resp.status_code == 403

    # getUserInfo roles 为空（不回退下发旧字符串）
    resp = await admin.client.get("/api/auth/getUserInfo", headers=user_headers)
    assert resp.status_code == 200, resp.text
    user_info = resp.json()["data"]
    assert user_info["roles"] == []
    assert user_info["buttons"] == []
    assert user_info["menus"] == []

    # DB：user_role 行清空 + role 字符串同步清空
    async with admin.maker() as session:
        user = (
            await session.execute(select(UserModel).where(UserModel.id == user_id))
        ).scalar_one()
        assert user.role == ""
        rows = list(
            (
                await session.execute(
                    select(UserRole).where(UserRole.user_id == user_id)
                )
            ).scalars().all()
        )
    assert rows == []


# ============================================================================
# 5. 软删（禁用）
# ============================================================================

async def test_soft_delete_invalidates_token(admin):
    """软删：旧 token 立即 401（token_version+1）；重复删 409"""
    headers = await _admin_headers(admin)
    resp = await admin.client.post(
        USERS_URL,
        json={
            "username": "softdel",
            "name": "待禁用",
            "role_codes": ["viewer"],
            "password": "Passw0rd123",
        },
        headers=headers,
    )
    user_id = resp.json()["data"]["id"]

    # 该用户登录拿 token
    login = await admin.client.post(
        "/api/auth/login-local", json={"userName": "softdel", "password": "Passw0rd123"}
    )
    user_headers = {"Authorization": f"Bearer {login.json()['data']['token']}"}
    resp = await admin.client.get(f"{USERS_URL}/me", headers=user_headers)
    assert resp.status_code == 200, resp.text

    # 管理员软删（status=0 + tv+1 + 吊销全部 refresh）
    resp = await admin.client.delete(f"{USERS_URL}/{user_id}", headers=headers)
    assert resp.status_code == 200, resp.text

    # 旧 token 立即失效
    resp = await admin.client.get(f"{USERS_URL}/me", headers=user_headers)
    assert resp.status_code == 401

    # 旧 refresh 也被吊销
    refresh = login.json()["data"]["refreshToken"]
    resp = await admin.client.post(
        "/api/auth/refreshToken", json={"refreshToken": refresh}
    )
    assert resp.status_code == 401

    # 重复删 → 409
    resp = await admin.client.delete(f"{USERS_URL}/{user_id}", headers=headers)
    assert resp.status_code == 409


# ============================================================================
# 5b. 状态禁用即吊销会话（J3）
# ============================================================================

async def test_disable_status_revokes_sessions(admin):
    """PUT /{user_id}/status 置 0：旧 access 因 token_version+1 立即 401，refresh 被吊销"""
    headers = await _admin_headers(admin)
    resp = await admin.client.post(
        USERS_URL,
        json={
            "username": "disableme",
            "name": "待禁用",
            "role_codes": ["viewer"],
            "password": "Passw0rd123",
        },
        headers=headers,
    )
    assert resp.status_code == 200, resp.text
    user_id = resp.json()["data"]["id"]

    login = await admin.client.post(
        "/api/auth/login-local", json={"userName": "disableme", "password": "Passw0rd123"}
    )
    assert login.status_code == 200, login.text
    user_headers = {"Authorization": f"Bearer {login.json()['data']['token']}"}
    refresh_token = login.json()["data"]["refreshToken"]

    # 管理员通过状态端点禁用（status=0 → tv+1 + 吊销全部 refresh）
    resp = await admin.client.put(
        f"{USERS_URL}/{user_id}/status", json={"status": 0}, headers=headers
    )
    assert resp.status_code == 200, resp.text

    # 旧 access：token_version 已落后 → 401
    resp = await admin.client.get(f"{USERS_URL}/me", headers=user_headers)
    assert resp.status_code == 401

    # 旧 refresh：已吊销 → 401
    resp = await admin.client.post(
        "/api/auth/refreshToken", json={"refreshToken": refresh_token}
    )
    assert resp.status_code == 401

    # DB：token_version 已 +1（原子自增，非读改写）
    async with admin.maker() as session:
        user = (
            await session.execute(select(UserModel).where(UserModel.id == user_id))
        ).scalar_one()
        assert user.status == 0
        assert user.token_version == 1


# ============================================================================
# 6. 重置密码
# ============================================================================

async def test_reset_password_flow(admin):
    """重置密码：明文临时密码只返一次、旧 token 失效、临时密码可登录 + mustChangePassword"""
    headers = await _admin_headers(admin)
    resp = await admin.client.post(
        USERS_URL,
        json={
            "username": "resetme",
            "name": "待重置",
            "role_codes": ["viewer"],
            "password": "OldPass12345",
        },
        headers=headers,
    )
    user_id = resp.json()["data"]["id"]

    login = await admin.client.post(
        "/api/auth/login-local", json={"userName": "resetme", "password": "OldPass12345"}
    )
    old_headers = {"Authorization": f"Bearer {login.json()['data']['token']}"}

    # 管理员重置 → 响应返回明文临时密码一次
    resp = await admin.client.put(f"{USERS_URL}/{user_id}/reset-password", headers=headers)
    assert resp.status_code == 200, resp.text
    temp_password = resp.json()["data"]["tempPassword"]
    assert len(temp_password) == 12
    assert temp_password.isalnum()

    # 旧 token 失效（tv+1）
    resp = await admin.client.get(f"{USERS_URL}/me", headers=old_headers)
    assert resp.status_code == 401

    # 临时密码可登录，且 mustChangePassword=True
    login2 = await admin.client.post(
        "/api/auth/login-local", json={"userName": "resetme", "password": temp_password}
    )
    assert login2.status_code == 200, login2.text
    assert login2.json()["data"]["mustChangePassword"] is True

    # 旧密码不再可用
    login3 = await admin.client.post(
        "/api/auth/login-local", json={"userName": "resetme", "password": "OldPass12345"}
    )
    assert login3.status_code == 401


# ============================================================================
# 7. 列表筛选：dept_id / role（user_role join + 存量字符串回退）
# ============================================================================

async def test_list_filters_dept_and_role(admin):
    """dept_id 走 user_dept join；role 优先 user_role、无行回退 role 字符串"""
    headers = await _admin_headers(admin)
    dept = await _make_dept(admin, "筛选部门")

    # A：POST 建号（user_role 行 viewer + role 字符串 viewer）+ 部门归属
    resp = await admin.client.post(
        USERS_URL,
        json={
            "username": "filter_a",
            "name": "筛选A",
            "role_codes": ["viewer"],
            "dept_assignments": [{"dept_id": str(dept.id), "is_primary": True}],
        },
        headers=headers,
    )
    assert resp.status_code == 200, resp.text
    user_a_id = resp.json()["data"]["id"]

    # B：直插存量用户（role 字符串 developer，无 user_role 行）
    user_b = await _make_user(
        admin.maker, username="filter_b", password="Passw0rd123", role="developer"
    )
    # C：user_role 挂 viewer 但 role 字符串仍是 developer（桥接冲突时以 user_role 为准）
    user_c = await _make_user(
        admin.maker, username="filter_c", password="Passw0rd123", role="developer"
    )
    viewer_role = await _get_role(admin, "viewer")
    async with admin.maker() as session:
        session.add(UserRole(user_id=str(user_c.id), role_id=str(viewer_role.id)))
        await session.commit()

    def _usernames(payload) -> set[str]:
        return {r["username"] for r in payload["rows"]}

    # dept_id 筛选：只有 A 挂了部门
    resp = await admin.client.get(
        f"{USERS_URL}", params={"dept_id": str(dept.id)}, headers=headers
    )
    assert resp.status_code == 200, resp.text
    assert _usernames(resp.json()["data"]) == {"filter_a"}

    # role=viewer：A（user_role）+ C（user_role 优先于 role 字符串）
    resp = await admin.client.get(
        f"{USERS_URL}", params={"role": "viewer"}, headers=headers
    )
    assert resp.status_code == 200, resp.text
    assert _usernames(resp.json()["data"]) == {"filter_a", "filter_c"}

    # role=developer：B（无 user_role 行回退字符串）；C 不命中（user_role 行存在时不回退）
    resp = await admin.client.get(
        f"{USERS_URL}", params={"role": "developer"}, headers=headers
    )
    assert resp.status_code == 200, resp.text
    assert _usernames(resp.json()["data"]) == {"filter_b"}

    # 列表行含 name / roleCodes（回显角色标签用）
    resp = await admin.client.get(USERS_URL, params={"pageSize": 100}, headers=headers)
    assert resp.status_code == 200, resp.text
    row_a = next(r for r in resp.json()["data"]["rows"] if r["username"] == "filter_a")
    assert row_a["name"] == "筛选A"
    assert row_a["roleCodes"] == ["viewer"]
    row_b = next(r for r in resp.json()["data"]["rows"] if r["username"] == "filter_b")
    # 存量用户无 user_role 行 → roleCodes 回退 role 字符串
    assert row_b["roleCodes"] == ["developer"]


async def test_get_user_detail(admin):
    """GET /{user_id}：编辑抽屉回显（role_codes + dept_assignments 含 is_primary）"""
    headers = await _admin_headers(admin)
    dept = await _make_dept(admin, "详情部门")

    resp = await admin.client.post(
        USERS_URL,
        json={
            "username": "detailme",
            "name": "详情用户",
            "role_codes": ["developer", "viewer"],
            "dept_assignments": [{"dept_id": str(dept.id), "is_primary": True}],
        },
        headers=headers,
    )
    assert resp.status_code == 200, resp.text
    user_id = resp.json()["data"]["id"]

    resp = await admin.client.get(f"{USERS_URL}/{user_id}", headers=headers)
    assert resp.status_code == 200, resp.text
    data = resp.json()["data"]
    assert data["username"] == "detailme"
    assert data["name"] == "详情用户"
    assert sorted(data["role_codes"]) == ["developer", "viewer"]
    assert data["dept_assignments"] == [
        {"dept_id": str(dept.id), "is_primary": True, "position_id": None}
    ]

    # 不存在的用户 → 404
    resp = await admin.client.get(f"{USERS_URL}/{uuid4()}", headers=headers)
    assert resp.status_code == 404
