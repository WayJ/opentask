"""用户中心播种幂等性测试（SQLite 内存库，只建 permission/role/role_permission）"""
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

import opentask.models  # noqa: F401 全量注册（FK 字符串引用需要）
from opentask.models.base import DBModel
from opentask.models.user_center import Permission, Role, RolePermission
from opentask.services.user_center import permission_defs
from opentask.services.user_center import seed as seed_mod
from opentask.services.user_center.seed import seed_user_center

# 只建权限播种涉及的 3 张表（无 FK 引用 user 表）
TABLES = ("permission", "role", "role_permission")


@pytest.fixture
async def session_maker():
    """SQLite 内存库会话工厂"""
    engine = create_async_engine("sqlite+aiosqlite://")
    tables = [DBModel.metadata.tables[n] for n in TABLES]
    async with engine.begin() as conn:
        await conn.run_sync(lambda m: DBModel.metadata.create_all(m, tables=tables))
    yield async_sessionmaker(engine, expire_on_commit=False)
    await engine.dispose()


async def _role_perm_codes(session: AsyncSession, role_code: str) -> set[str]:
    """查询某角色当前的权限码集合"""
    result = await session.execute(
        select(Permission.code)
        .join(RolePermission, RolePermission.permission_id == Permission.id)
        .join(Role, Role.id == RolePermission.role_id)
        .where(Role.code == role_code)
    )
    return set(result.scalars().all())


async def test_seed_creates_roles_and_permissions(session_maker):
    """播种后：role 4 条、permission 数与字典一致、admin 拥有全部权限"""
    async with session_maker() as session:
        counts = await seed_user_center(session)

        role_count = len((await session.execute(select(Role))).scalars().all())
        perm_count = len((await session.execute(select(Permission))).scalars().all())
        assert role_count == 4
        assert perm_count == len(permission_defs.PERMISSIONS)
        assert counts == {"permissions": len(permission_defs.PERMISSIONS), "roles": 4}

        # admin 拥有全部权限码
        admin_codes = await _role_perm_codes(session, "admin")
        assert admin_codes == permission_defs.permission_codes()

        # 角色属性正确
        roles = {r.code: r for r in (await session.execute(select(Role))).scalars().all()}
        assert roles["maintainer"].data_scope == "ALL"
        assert roles["developer"].data_scope == "DEPT_AND_CHILD"
        assert roles["viewer"].data_scope == "SELF"
        assert all(r.is_system for r in roles.values())

        # maintainer 权限集：全部业务四操作 + 用户管理菜单 + 2 个管理按钮
        # （manage:user:migrate 为 admin 专属，seed 只给 admin 全量码）
        maintainer_codes = await _role_perm_codes(session, "maintainer")
        business = {
            f"{m}:{op}"
            for m in ("requirement", "issue", "project", "knowledge", "task")
            for op in ("view", "create", "update", "delete")
        }
        assert maintainer_codes == business | {
            "menu:manage_user", "manage:user:status", "manage:user:role",
        }
        assert "manage:user:migrate" not in maintainer_codes


async def test_seed_idempotent(session_maker):
    """连跑两遍：计数与 role_permission 均不变"""
    async with session_maker() as session:
        first = await seed_user_center(session)

        # 记录第一遍后各角色权限码
        snapshot = {
            code: await _role_perm_codes(session, code)
            for code in ("admin", "maintainer", "developer", "viewer")
        }

        second = await seed_user_center(session)
        assert second == first

        for code, expected in snapshot.items():
            assert await _role_perm_codes(session, code) == expected

        perm_count = len((await session.execute(select(Permission))).scalars().all())
        rp_count = len((await session.execute(select(RolePermission))).all())
        assert perm_count == len(permission_defs.PERMISSIONS)
        assert rp_count == sum(len(v) for v in snapshot.values())


async def test_seed_removes_stale_role_permissions(session_maker, monkeypatch):
    """字典演进：字典移除某权限码后重跑，系统角色 role_permission 对应行被清"""
    async with session_maker() as session:
        await seed_user_center(session)
        assert "task:delete" in await _role_perm_codes(session, "admin")

        # 字典移除 task:delete 后重跑
        reduced = [p for p in permission_defs.PERMISSIONS if p["code"] != "task:delete"]
        monkeypatch.setattr(seed_mod, "PERMISSIONS", reduced)

        await seed_user_center(session)

        for code in ("admin", "maintainer", "developer", "viewer"):
            assert "task:delete" not in await _role_perm_codes(session, code)

        # admin 权限数 == 字典长度 - 1
        assert len(await _role_perm_codes(session, "admin")) == len(reduced)
        # permission 行保留（字典行不删，仅解除角色关联）
        result = await session.execute(
            select(Permission).where(Permission.code == "task:delete")
        )
        assert result.scalar_one_or_none() is not None
