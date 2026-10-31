"""dept_service 单元测试：path 物化路径、子树移动防环、非空删除拒绝、
用户部门归属覆盖式分配与 is_primary 校验（SQLite 内存库）"""
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

import opentask.models  # noqa: F401 全量注册（FK 字符串引用需要）
from opentask.models.base import DBModel
from opentask.models.user.model import UserModel
from opentask.models.user_center.model import Department, Position, UserDept
from opentask.errors import ValidationError
from opentask.repositories.base import NotFoundError
from opentask.services.user_center.dept_service import DeptService

# 部门树 + 用户归属涉及的 4 张表
TABLES = ("user", "department", "user_dept", "position")


@pytest.fixture
async def session_maker():
    """SQLite 内存库会话工厂"""
    engine = create_async_engine("sqlite+aiosqlite://")
    tables = [DBModel.metadata.tables[n] for n in TABLES]
    async with engine.begin() as conn:
        await conn.run_sync(lambda m: DBModel.metadata.create_all(m, tables=tables))
    maker = async_sessionmaker(engine, expire_on_commit=False)
    yield maker
    await engine.dispose()


async def _make_user(session: AsyncSession) -> UserModel:
    """建一个最小可用用户"""
    tag = uuid4().hex[:8]
    user = UserModel(name=f"用户-{tag}", username=f"u-{tag}", role="viewer")
    session.add(user)
    await session.flush()
    return user


def _item(dept_id: str, is_primary: bool = False, position_id: str | None = None):
    """归属行（service 鸭子类型：dept_id / is_primary / position_id）"""
    return SimpleNamespace(dept_id=dept_id, is_primary=is_primary, position_id=position_id)


async def _build_tree(session: AsyncSession, svc: DeptService) -> dict[str, Department]:
    """造 3 层树 root → child → grand，外加独立根 other"""
    root = await svc.create_dept("root")
    child = await svc.create_dept("child", parent_id=str(root.id))
    grand = await svc.create_dept("grand", parent_id=str(child.id))
    other = await svc.create_dept("other")
    return {"root": root, "child": child, "grand": grand, "other": other}


async def _get_dept(session: AsyncSession, dept_id: str) -> Department:
    return (
        await session.execute(select(Department).where(Department.id == dept_id))
    ).scalar_one()


# ---- 1. 创建与 path ----


async def test_create_three_levels_paths(session_maker):
    """建根/子/孙：path 逐层拼接（/{id} 格式，三层正确）"""
    async with session_maker() as session:
        svc = DeptService(session)
        root = await svc.create_dept("root")
        child = await svc.create_dept("child", parent_id=str(root.id))
        grand = await svc.create_dept("grand", parent_id=str(child.id), sort=5)

        assert root.path == f"/{root.id}"
        assert child.path == f"/{root.id}/{child.id}"
        assert grand.path == f"/{root.id}/{child.id}/{grand.id}"
        assert root.parent_id is None
        assert str(child.parent_id) == str(root.id)
        assert grand.sort == 5


async def test_create_with_missing_parent_404(session_maker):
    """parent_id 不存在 → NotFoundError"""
    async with session_maker() as session:
        with pytest.raises(NotFoundError):
            await DeptService(session).create_dept("x", parent_id=str(uuid4()))


# ---- 2. 子树移动 ----


async def test_move_subtree_recalculates_paths(session_maker):
    """移动 child 到 other 下：child 与孙 grand 的 path 前缀全变"""
    async with session_maker() as session:
        svc = DeptService(session)
        d = await _build_tree(session, svc)

        moved = await svc.update_dept(str(d["child"].id), parent_id=str(d["other"].id))

        assert str(moved.parent_id) == str(d["other"].id)
        assert moved.path == f"/{d['other'].id}/{d['child'].id}"
        grand = await _get_dept(session, str(d["grand"].id))
        assert grand.path == f"/{d['other'].id}/{d['child'].id}/{d['grand'].id}"
        # 根与 other 自身不受影响
        assert (await _get_dept(session, str(d["root"].id))).path == f"/{d['root'].id}"
        assert (await _get_dept(session, str(d["other"].id))).path == f"/{d['other'].id}"


async def test_move_to_root(session_maker):
    """显式 parent_id=None：移为根部门，子孙跟随"""
    async with session_maker() as session:
        svc = DeptService(session)
        d = await _build_tree(session, svc)

        moved = await svc.update_dept(str(d["child"].id), parent_id=None)

        assert moved.parent_id is None
        assert moved.path == f"/{d['child'].id}"
        grand = await _get_dept(session, str(d["grand"].id))
        assert grand.path == f"/{d['child'].id}/{d['grand'].id}"


async def test_move_without_parent_field_keeps_tree(session_maker):
    """只改 name/sort：parent_id 未提供，不触发移动"""
    async with session_maker() as session:
        svc = DeptService(session)
        d = await _build_tree(session, svc)

        dept = await svc.update_dept(str(d["child"].id), name="child2", sort=9)

        assert dept.name == "child2"
        assert dept.sort == 9
        assert dept.path == f"/{d['root'].id}/{d['child'].id}"
        assert str(dept.parent_id) == str(d["root"].id)


# ---- 3. 防环 ----


async def test_move_under_descendant_rejected(session_maker):
    """把自己移到自己的子孙下 → 409"""
    async with session_maker() as session:
        svc = DeptService(session)
        d = await _build_tree(session, svc)

        with pytest.raises(HTTPException) as exc:
            await svc.update_dept(str(d["root"].id), parent_id=str(d["grand"].id))
        assert exc.value.status_code == 409

        # 数据未变：root 仍是根，孙仍在原子树
        assert (await _get_dept(session, str(d["root"].id))).path == f"/{d['root'].id}"
        assert (
            await _get_dept(session, str(d["grand"].id))
        ).path == f"/{d['root'].id}/{d['child'].id}/{d['grand'].id}"


async def test_move_under_itself_rejected(session_maker):
    """把自己移到自己下 → 409"""
    async with session_maker() as session:
        svc = DeptService(session)
        d = await _build_tree(session, svc)

        with pytest.raises(HTTPException) as exc:
            await svc.update_dept(str(d["child"].id), parent_id=str(d["child"].id))
        assert exc.value.status_code == 409


# ---- 4. 删除 ----


async def test_delete_with_children_rejected(session_maker):
    """有子部门 → 409"""
    async with session_maker() as session:
        svc = DeptService(session)
        d = await _build_tree(session, svc)

        with pytest.raises(HTTPException) as exc:
            await svc.delete_dept(str(d["root"].id))
        assert exc.value.status_code == 409


async def test_delete_with_members_rejected(session_maker):
    """有成员（user_dept 有行）→ 409"""
    async with session_maker() as session:
        svc = DeptService(session)
        d = await _build_tree(session, svc)
        user = await _make_user(session)
        session.add(
            UserDept(user_id=str(user.id), dept_id=str(d["grand"].id), is_primary=True)
        )
        await session.flush()

        with pytest.raises(HTTPException) as exc:
            await svc.delete_dept(str(d["grand"].id))
        assert exc.value.status_code == 409


async def test_delete_leaf_succeeds(session_maker):
    """叶子且无成员 → 删除成功，查无此行"""
    async with session_maker() as session:
        svc = DeptService(session)
        d = await _build_tree(session, svc)

        await svc.delete_dept(str(d["grand"].id))

        result = await session.execute(
            select(Department).where(Department.id == str(d["grand"].id))
        )
        assert result.scalar_one_or_none() is None


# ---- 5. 用户部门归属 ----


async def test_assign_user_depts_overwrite(session_maker):
    """覆盖式分配：多部门 + 恰一 primary；重分配后旧行被替换"""
    async with session_maker() as session:
        svc = DeptService(session)
        d = await _build_tree(session, svc)
        user = await _make_user(session)

        count = await svc.assign_user_depts(
            str(user.id),
            [
                _item(str(d["root"].id), is_primary=True),
                _item(str(d["child"].id)),
            ],
        )
        assert count == 2
        rows = (
            await session.execute(
                select(UserDept).where(UserDept.user_id == str(user.id))
            )
        ).scalars().all()
        assert {(r.dept_id, r.is_primary) for r in rows} == {
            (str(d["root"].id), True),
            (str(d["child"].id), False),
        }

        # 覆盖式重分配：只剩 other
        await svc.assign_user_depts(
            str(user.id), [_item(str(d["other"].id), is_primary=True)]
        )
        rows = (
            await session.execute(
                select(UserDept).where(UserDept.user_id == str(user.id))
            )
        ).scalars().all()
        assert [r.dept_id for r in rows] == [str(d["other"].id)]


async def test_assign_primary_validation(session_maker):
    """0 行或 2 行 is_primary=true → 400（ValidationError）"""
    async with session_maker() as session:
        svc = DeptService(session)
        d = await _build_tree(session, svc)
        user = await _make_user(session)

        with pytest.raises(ValidationError):
            await svc.assign_user_depts(
                str(user.id), [_item(str(d["root"].id))]
            )  # 0 行 primary
        with pytest.raises(ValidationError):
            await svc.assign_user_depts(
                str(user.id),
                [
                    _item(str(d["root"].id), is_primary=True),
                    _item(str(d["child"].id), is_primary=True),
                ],
            )  # 2 行 primary
        # 校验失败不落任何行
        rows = (
            await session.execute(
                select(UserDept).where(UserDept.user_id == str(user.id))
            )
        ).scalars().all()
        assert rows == []


async def test_assign_empty_clears(session_maker):
    """空数组 = 清空归属（允许）"""
    async with session_maker() as session:
        svc = DeptService(session)
        d = await _build_tree(session, svc)
        user = await _make_user(session)
        await svc.assign_user_depts(
            str(user.id), [_item(str(d["root"].id), is_primary=True)]
        )

        assert await svc.assign_user_depts(str(user.id), []) == 0

        rows = (
            await session.execute(
                select(UserDept).where(UserDept.user_id == str(user.id))
            )
        ).scalars().all()
        assert rows == []


async def test_assign_unknown_dept_or_user_rejected(session_maker):
    """部门不存在 → 400；用户不存在 → 404"""
    async with session_maker() as session:
        svc = DeptService(session)
        d = await _build_tree(session, svc)
        user = await _make_user(session)

        with pytest.raises(ValidationError):
            await svc.assign_user_depts(
                str(user.id), [_item(str(uuid4()), is_primary=True)]
            )
        with pytest.raises(NotFoundError):
            await svc.assign_user_depts(
                str(uuid4()), [_item(str(d["root"].id), is_primary=True)]
            )


async def test_assign_with_position(session_maker):
    """带岗位的归属行：position_id 校验存在并原样落库"""
    async with session_maker() as session:
        svc = DeptService(session)
        d = await _build_tree(session, svc)
        user = await _make_user(session)
        position = Position(name="前端工程师")
        session.add(position)
        await session.flush()

        await svc.assign_user_depts(
            str(user.id),
            [_item(str(d["root"].id), is_primary=True, position_id=str(position.id))],
        )

        row = (
            await session.execute(
                select(UserDept).where(UserDept.user_id == str(user.id))
            )
        ).scalar_one()
        assert str(row.position_id) == str(position.id)

        # 岗位不存在 → 400
        with pytest.raises(ValidationError):
            await svc.assign_user_depts(
                str(user.id),
                [_item(str(d["root"].id), is_primary=True, position_id=str(uuid4()))],
            )


# ---- 6. 启禁用 ----


async def test_disable_and_enable_dept(session_maker):
    """禁用/启用部门：status 翻转；非法值 → 400"""
    async with session_maker() as session:
        svc = DeptService(session)
        root = await svc.create_dept("root")

        dept = await svc.set_dept_status(str(root.id), 0)
        assert dept.status == 0
        assert (await _get_dept(session, str(root.id))).status == 0

        dept = await svc.set_dept_status(str(root.id), 1)
        assert dept.status == 1

        with pytest.raises(ValidationError):
            await svc.set_dept_status(str(root.id), 2)


# ---- 7. 树构建 ----


async def test_get_tree_nesting(session_maker):
    """全表内存组树：root>child>grand 嵌套 + other 独立根；禁用部门仍在树中"""
    async with session_maker() as session:
        svc = DeptService(session)
        d = await _build_tree(session, svc)
        await svc.set_dept_status(str(d["grand"].id), 0)

        tree = await svc.get_tree()

        roots = {n["name"]: n for n in tree}
        assert set(roots) == {"root", "other"}
        child = roots["root"]["children"][0]
        assert child["name"] == "child"
        grand = child["children"][0]
        assert grand["name"] == "grand"
        assert grand["status"] == 0
        assert grand["path"] == f"/{d['root'].id}/{d['child'].id}/{d['grand'].id}"
        # 叶子节点不带 children 键（naive-ui 将 children=[] 视为非叶子，见 _to_node 注释）
        assert "children" not in roots["other"]
