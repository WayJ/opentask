"""rbac_service 单元测试：角色桥接/并集、数据范围、可见部门集、过滤注入（SQLite 内存库）"""
from uuid import uuid4

import pytest
from sqlalchemy import Column, MetaData, String, Table, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

import opentask.models  # noqa: F401 全量注册（FK 字符串引用需要）
from opentask.models.base import DBModel
from opentask.models.user.model import UserModel
from opentask.models.user_center.model import (
    Department,
    Role,
    RoleDept,
    UserDept,
    UserRole,
)
from opentask.services.user_center.permission_defs import permission_codes
from opentask.services.user_center.rbac_service import RbacService
from opentask.services.user_center.seed import seed_user_center

# RBAC 涉及的 8 张表（user + 7 张关联/字典表）
TABLES = (
    "user",
    "role",
    "permission",
    "role_permission",
    "user_role",
    "role_dept",
    "department",
    "user_dept",
)

# apply_data_scope 的目标表（独立 MetaData，不污染 DBModel.metadata）：
# 模拟业务资源行，带 dept_id 与 creator_id
RESOURCE_META = MetaData()
resource = Table(
    "rbac_resource",
    RESOURCE_META,
    Column("id", String(36), primary_key=True),
    Column("name", String(50), nullable=False),
    Column("dept_id", String(36), nullable=False),
    Column("creator_id", String(36), nullable=False),
)


@pytest.fixture
async def session_maker():
    """SQLite 内存库会话工厂（播种权限点 + 系统角色）"""
    engine = create_async_engine("sqlite+aiosqlite://")
    tables = [DBModel.metadata.tables[n] for n in TABLES]
    async with engine.begin() as conn:
        await conn.run_sync(lambda m: DBModel.metadata.create_all(m, tables=tables))
        await conn.run_sync(RESOURCE_META.create_all)
    maker = async_sessionmaker(engine, expire_on_commit=False)
    async with maker() as session:
        await seed_user_center(session)
    yield maker
    await engine.dispose()


async def _make_user(session: AsyncSession, role: str = "viewer") -> UserModel:
    """建一个最小可用用户（role 为存量字符串字段）"""
    tag = uuid4().hex[:8]
    user = UserModel(name=f"用户-{tag}", username=f"u-{tag}", role=role)
    session.add(user)
    await session.flush()
    return user


async def _get_role(session: AsyncSession, code: str) -> Role:
    return (await session.execute(select(Role).where(Role.code == code))).scalar_one()


def _dept(name: str, path: str, parent_id: str | None = None) -> Department:
    return Department(name=name, path=path, parent_id=parent_id)


# ---- 1. 角色桥接 ----


async def test_legacy_role_string_bridge(session_maker):
    """无 user_role 行 + user.role='viewer' → 桥接到 viewer 角色，权限为 viewer 集"""
    async with session_maker() as session:
        user = await _make_user(session, role="viewer")
        svc = RbacService(session)

        assert await svc.get_user_role_codes(user) == ["viewer"]
        viewer_perms = await svc.get_user_permissions(user)
        assert viewer_perms == {
            f"{m}:view" for m in ("requirement", "issue", "project", "knowledge", "task")
        }
        # viewer 是 SELF 档
        assert await svc.get_data_scope(user) == "SELF"


async def test_user_role_rows_take_precedence(session_maker):
    """user.role='viewer' 但 user_role 挂 admin → 以 user_role 为准（admin 全权限）"""
    async with session_maker() as session:
        user = await _make_user(session, role="viewer")
        admin = await _get_role(session, "admin")
        session.add(UserRole(user_id=str(user.id), role_id=str(admin.id)))
        await session.flush()

        svc = RbacService(session)
        assert await svc.get_user_role_codes(user) == ["admin"]
        assert await svc.get_user_permissions(user) == permission_codes()
        assert await svc.get_data_scope(user) == "ALL"


# ---- 2. 多角色并集与最宽数据范围 ----


async def test_multi_role_union_and_widest_scope(session_maker):
    """developer + viewer：权限并集；数据范围取最宽 DEPT_AND_CHILD"""
    async with session_maker() as session:
        user = await _make_user(session, role="developer")
        for code in ("developer", "viewer"):
            role = await _get_role(session, code)
            session.add(UserRole(user_id=str(user.id), role_id=str(role.id)))
        await session.flush()

        svc = RbacService(session)
        assert sorted(await svc.get_user_role_codes(user)) == ["developer", "viewer"]

        # 并集：developer 的 view/create/update + viewer 的 view
        perms = await svc.get_user_permissions(user)
        expected = {
            f"{m}:{op}"
            for m in ("requirement", "issue", "project", "knowledge", "task")
            for op in ("view", "create", "update")
        }
        assert perms == expected
        # 最宽档：DEPT_AND_CHILD(3) > SELF(0)
        assert await svc.get_data_scope(user) == "DEPT_AND_CHILD"


async def test_no_role_defaults_to_self(session_maker):
    """无 user_role 行且 role 字符串查不到角色 → 默认 SELF、空权限"""
    async with session_maker() as session:
        user = await _make_user(session, role="ghost-role")
        svc = RbacService(session)

        assert await svc.get_user_role_codes(user) == []
        assert await svc.get_user_permissions(user) == set()
        assert await svc.get_data_scope(user) == "SELF"
        # SELF → 空集（非 None）
        assert await svc.get_visible_dept_ids(user) == set()


# ---- 2.5 停用权限点过滤（Phase 5 Task 1）----


async def test_disabled_permission_excluded(session_maker):
    """停用权限码后 get_user_permissions 不再包含该码（require_permission 即时 403）"""
    from opentask.models.user_center.model import Permission

    async with session_maker() as session:
        user = await _make_user(session, role="maintainer")
        svc = RbacService(session)

        before = await svc.get_user_permissions(user)
        assert "manage:user:status" in before

        perm = (
            await session.execute(
                select(Permission).where(Permission.code == "manage:user:status")
            )
        ).scalar_one()
        perm.status = 0
        await session.flush()

        after = await svc.get_user_permissions(user)
        assert "manage:user:status" not in after
        # 其余权限不受影响
        assert before - {"manage:user:status"} == after


# ---- 3. 可见部门集 ----


async def _build_dept_tree(session: AsyncSession) -> dict[str, Department]:
    """造 3 层部门树：/root → /root/child → /root/child/grand，外加兄弟 /other"""
    depts = {
        "root": _dept("root", "/root"),
        "child": _dept("child", "/root/child"),
        "grand": _dept("grand", "/root/child/grand"),
        "other": _dept("other", "/other"),
    }
    for d in depts.values():
        session.add(d)
    await session.flush()
    # 建立父子关系（parent_id 事后补，path 已带层级）
    depts["child"].parent_id = str(depts["root"].id)
    depts["grand"].parent_id = str(depts["child"].id)
    await session.flush()
    return depts


async def test_visible_depts_dept_scope(session_maker):
    """DEPT 档：只含所属部门，不展开子树"""
    async with session_maker() as session:
        user = await _make_user(session, role="viewer")
        depts = await _build_dept_tree(session)
        # 手造一个 DEPT 档角色（系统四角色无 DEPT 档）
        dept_role = Role(code="dept-only", name="仅本部门", data_scope="DEPT")
        session.add(dept_role)
        await session.flush()
        session.add(UserRole(user_id=str(user.id), role_id=str(dept_role.id)))
        session.add(UserDept(user_id=str(user.id), dept_id=str(depts["child"].id), is_primary=True))
        await session.flush()

        svc = RbacService(session)
        assert await svc.get_data_scope(user) == "DEPT"
        assert await svc.get_visible_dept_ids(user) == {str(depts["child"].id)}


async def test_visible_depts_dept_and_child_scope(session_maker):
    """DEPT_AND_CHILD：所属部门 + 全部子孙（3 层树验证），不含兄弟部门"""
    async with session_maker() as session:
        user = await _make_user(session, role="developer")
        depts = await _build_dept_tree(session)
        developer = await _get_role(session, "developer")
        session.add(UserRole(user_id=str(user.id), role_id=str(developer.id)))
        session.add(UserDept(user_id=str(user.id), dept_id=str(depts["root"].id), is_primary=True))
        await session.flush()

        svc = RbacService(session)
        assert await svc.get_data_scope(user) == "DEPT_AND_CHILD"
        visible = await svc.get_visible_dept_ids(user)
        assert visible == {
            str(depts["root"].id),
            str(depts["child"].id),
            str(depts["grand"].id),
        }
        # 兄弟部门不可见
        assert str(depts["other"].id) not in visible


async def test_visible_depts_custom_scope(session_maker):
    """CUSTOM：role_dept ∪ user_dept"""
    async with session_maker() as session:
        user = await _make_user(session, role="viewer")
        depts = await _build_dept_tree(session)
        custom_role = Role(code="custom-role", name="自定义范围", data_scope="CUSTOM")
        session.add(custom_role)
        await session.flush()
        session.add(UserRole(user_id=str(user.id), role_id=str(custom_role.id)))
        # 用户挂在 child，角色自定义授 grand + other
        session.add(UserDept(user_id=str(user.id), dept_id=str(depts["child"].id), is_primary=True))
        session.add(RoleDept(role_id=str(custom_role.id), dept_id=str(depts["grand"].id)))
        session.add(RoleDept(role_id=str(custom_role.id), dept_id=str(depts["other"].id)))
        await session.flush()

        svc = RbacService(session)
        assert await svc.get_data_scope(user) == "CUSTOM"
        assert await svc.get_visible_dept_ids(user) == {
            str(depts["child"].id),  # user_dept
            str(depts["grand"].id),  # role_dept
            str(depts["other"].id),  # role_dept
        }


async def test_visible_depts_all_scope(session_maker):
    """ALL：返回 None（调用方不过滤）"""
    async with session_maker() as session:
        user = await _make_user(session, role="admin")
        svc = RbacService(session)
        assert await svc.get_data_scope(user) == "ALL"
        assert await svc.get_visible_dept_ids(user) is None


# ---- 4. apply_data_scope 过滤注入（实插数据执行查询） ----


async def _seed_resources(session: AsyncSession, depts: dict[str, Department], user_id: str):
    """每个部门插 1 行（creator=user_id），再插 1 行其他创建者的（child 部门）"""
    rows = []
    for key, d in depts.items():
        rows.append(
            {
                "id": uuid4().hex,
                "name": f"res-{key}",
                "dept_id": str(d.id),
                "creator_id": user_id,
            }
        )
    other_creator = uuid4().hex
    rows.append(
        {
            "id": uuid4().hex,
            "name": "res-child-other-creator",
            "dept_id": str(depts["child"].id),
            "creator_id": other_creator,
        }
    )
    await session.execute(resource.insert(), rows)
    return other_creator


async def _names(session: AsyncSession, stmt) -> set[str]:
    result = await session.execute(stmt)
    return {row["name"] for row in result.mappings().all()}


async def test_apply_data_scope_all_passthrough(session_maker):
    """ALL（None）→ 语句原样返回，全部行可见"""
    async with session_maker() as session:
        depts = await _build_dept_tree(session)
        user = await _make_user(session, role="admin")
        await _seed_resources(session, depts, str(user.id))

        svc = RbacService(session)
        stmt = svc.apply_data_scope(select(resource), None, resource.c.dept_id)
        assert await _names(session, stmt) == {
            "res-root",
            "res-child",
            "res-grand",
            "res-other",
            "res-child-other-creator",
        }


async def test_apply_data_scope_dept_filter(session_maker):
    """DEPT 档 → 只见白名单部门的行；creator 例外：本人创建的行始终可见"""
    async with session_maker() as session:
        depts = await _build_dept_tree(session)
        user = await _make_user(session, role="viewer")
        await _seed_resources(session, depts, str(user.id))

        svc = RbacService(session)

        # 无 creator_col：纯部门过滤（child + grand），root/other 不可见
        ids = {str(depts["child"].id), str(depts["grand"].id)}
        stmt = svc.apply_data_scope(select(resource), ids, resource.c.dept_id)
        assert await _names(session, stmt) == {
            "res-child",
            "res-child-other-creator",
            "res-grand",
        }

        # 带 creator_col：白名单外但本人创建的行（root/other）仍可见，
        # 白名单外且他人创建的行（child 上他人建的）不可见
        stmt = svc.apply_data_scope(
            select(resource),
            {str(depts["grand"].id)},
            resource.c.dept_id,
            creator_col=resource.c.creator_id,
            user_id=str(user.id),
        )
        assert await _names(session, stmt) == {
            "res-root",
            "res-child",
            "res-grand",
            "res-other",
        }


async def test_apply_data_scope_self_with_creator(session_maker):
    """SELF（空集）+ creator_col → 只见本人创建的行"""
    async with session_maker() as session:
        depts = await _build_dept_tree(session)
        user = await _make_user(session, role="viewer")
        await _seed_resources(session, depts, str(user.id))

        svc = RbacService(session)
        stmt = svc.apply_data_scope(
            select(resource), set(), resource.c.dept_id,
            creator_col=resource.c.creator_id, user_id=str(user.id),
        )
        assert await _names(session, stmt) == {
            "res-root",
            "res-child",
            "res-grand",
            "res-other",
        }


async def test_apply_data_scope_self_without_creator(session_maker):
    """SELF（空集）且无 creator_col → 结果恒空"""
    async with session_maker() as session:
        depts = await _build_dept_tree(session)
        user = await _make_user(session, role="viewer")
        await _seed_resources(session, depts, str(user.id))

        svc = RbacService(session)
        stmt = svc.apply_data_scope(select(resource), set(), resource.c.dept_id)
        assert await _names(session, stmt) == set()


async def test_apply_data_scope_no_creator_col(session_maker):
    """creator_col=None → 仅按部门过滤，无视创建者"""
    async with session_maker() as session:
        depts = await _build_dept_tree(session)
        user = await _make_user(session, role="viewer")
        await _seed_resources(session, depts, str(user.id))

        svc = RbacService(session)
        ids = {str(depts["child"].id)}
        stmt = svc.apply_data_scope(select(resource), ids, resource.c.dept_id)
        # child 部门两行都可见（含他人创建的）
        assert await _names(session, stmt) == {"res-child", "res-child-other-creator"}
