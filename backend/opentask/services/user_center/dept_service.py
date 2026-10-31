"""部门树服务：部门 CRUD/移动防环/树构建 + 用户部门归属覆盖式分配

path 物化路径约定：/{root_id}/{child_id}/...（每层 37 字符，String(500) 约 13 层）。
rbac_service.get_visible_dept_ids 依赖 path 前缀展开子树，
因此移动子树时必须同步重算自身与全部子孙的 path。

错误约定：
- NotFoundError → 404：部门/用户/岗位不存在；
- ValidationError → 400：is_primary 恰一行等请求校验失败；
- HTTPException(409)：防环（移到自身/子孙下）、删除非空部门
  （与 auth_service 一致，service 层直接抛 HTTPException 表达业务冲突）。

实现注意：UUIDMixin.id 是 init=False + insert_default，构造 Department 拿不到 id，
需先 flush 取回 id 再回填 path。
"""
from typing import Any, Sequence

from fastapi import HTTPException
from sqlalchemy import delete, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from opentask.models.user.model import UserModel
from opentask.models.user_center.model import Department, Position, UserDept
from opentask.errors import ValidationError
from opentask.repositories.base import NotFoundError

# update_dept 的"未提供"哨兵：区分"不动"与"显式传 None（移为根部门）"
UNSET: Any = object()


class DeptService:
    """部门树与用户部门归属管理"""

    def __init__(self, session: AsyncSession):
        self.session = session

    # ---- 内部工具 ----

    async def _get_dept(self, dept_id: str) -> Department:
        """按 id 查部门，不存在抛 NotFoundError"""
        result = await self.session.execute(
            select(Department).where(Department.id == dept_id)
        )
        dept = result.scalar_one_or_none()
        if dept is None:
            raise NotFoundError(f"部门不存在: {dept_id}")
        return dept

    @staticmethod
    def _is_in_subtree(path: str, subtree_root_path: str) -> bool:
        """path 是否位于 subtree_root_path 子树内（含自身）。

        精确前缀匹配（path == root 或以 "root/" 开头），
        避免直接 startswith 误伤同前缀兄弟（id 固定 36 位，正常数据不会出现，
        仍保持与 rbac_service.get_visible_dept_ids 相同的严格语义）。
        """
        return path == subtree_root_path or path.startswith(subtree_root_path + "/")

    @staticmethod
    def _to_node(dept: Department) -> dict:
        """部门 ORM 对象 → 树节点 dict（id 统一转 36 位字符串）

        叶子节点不带 children 键：naive-ui 的 NTree/NTreeSelect 将
        children=[] 视为"可展开的非叶子"，导致 check-strategy="child"
        下叶子复选框不渲染（用户抽屉部门无法勾选）。
        """
        return {
            "id": str(dept.id),
            "name": dept.name,
            "parent_id": str(dept.parent_id) if dept.parent_id else None,
            "path": dept.path,
            "sort": dept.sort,
            "status": dept.status,
        }

    # ---- 部门 CRUD ----

    async def create_dept(
        self, name: str, parent_id: str | None = None, sort: int = 0
    ) -> Department:
        """创建部门。parent_id 为空 = 根部门；path = 父path + "/" + 自身id"""
        parent = None
        if parent_id is not None:
            parent = await self._get_dept(parent_id)
        dept = Department(name=name, parent_id=parent_id, sort=sort, path="")
        self.session.add(dept)
        # 先 flush 取回 insert_default 生成的 id，才能计算 path
        await self.session.flush()
        dept.path = (parent.path if parent else "") + f"/{dept.id}"
        await self.session.flush()
        return dept

    async def update_dept(
        self,
        dept_id: str,
        *,
        name: str | None | Any = UNSET,
        parent_id: str | None | Any = UNSET,
        sort: int | None | Any = UNSET,
    ) -> Department:
        """更新部门。显式传 parent_id 且与当前不同 = 移动（重算子树 path）。

        UNSET 哨兵区分"字段未提供"与"显式传 None"（None = 移为根部门）。
        """
        dept = await self._get_dept(dept_id)
        if name is not UNSET and name is not None:
            dept.name = name
        if sort is not UNSET and sort is not None:
            dept.sort = sort
        if parent_id is not UNSET:
            current_parent = str(dept.parent_id) if dept.parent_id else None
            if parent_id != current_parent:
                await self._move_subtree(dept, parent_id)
        return dept

    async def _move_subtree(self, dept: Department, new_parent_id: str | None) -> None:
        """把 dept 移到 new_parent_id 下（None = 移为根），同步重算整棵子树 path。

        防环：新父不能是自身或自身的子孙，否则 409。
        部门量级小，子孙逐行在内存中做前缀替换回写。
        """
        old_path = dept.path
        parent = None
        if new_parent_id is not None:
            parent = await self._get_dept(new_parent_id)
            if parent.id == dept.id or self._is_in_subtree(parent.path, dept.path):
                raise HTTPException(
                    status_code=409, detail="不能把部门移动到自身或其子孙部门下"
                )
        new_path = (parent.path if parent else "") + f"/{dept.id}"

        result = await self.session.execute(
            select(Department).where(
                or_(
                    Department.path == old_path,
                    Department.path.like(old_path + "/%"),
                )
            )
        )
        for node in result.scalars().all():
            node.path = new_path + node.path[len(old_path):]
        dept.parent_id = str(parent.id) if parent else None
        await self.session.flush()

    async def set_dept_status(self, dept_id: str, status: int) -> Department:
        """启用/禁用部门（1/0）"""
        if status not in (0, 1):
            raise ValidationError("status 仅允许 0（禁用）或 1（启用）")
        dept = await self._get_dept(dept_id)
        dept.status = status
        await self.session.flush()
        return dept

    async def delete_dept(self, dept_id: str) -> None:
        """删除部门。有子部门或仍有成员（user_dept）→ 409。"""
        dept = await self._get_dept(dept_id)
        dept_id_str = str(dept.id)
        children = await self.session.execute(
            select(Department.id).where(Department.parent_id == dept_id_str).limit(1)
        )
        if children.first() is not None:
            raise HTTPException(status_code=409, detail="存在子部门，不能删除")
        members = await self.session.execute(
            select(UserDept.user_id).where(UserDept.dept_id == dept_id_str).limit(1)
        )
        if members.first() is not None:
            raise HTTPException(status_code=409, detail="部门下仍有成员，不能删除")
        await self.session.delete(dept)
        await self.session.flush()

    # ---- 树查询 ----

    async def get_tree(self) -> list[dict]:
        """全量拉取部门（量级小），内存组树。含禁用部门。"""
        result = await self.session.execute(
            select(Department).order_by(Department.sort, Department.name)
        )
        depts = list(result.scalars().all())
        nodes = {str(d.id): self._to_node(d) for d in depts}
        roots: list[dict] = []
        for dept in depts:
            node = nodes[str(dept.id)]
            parent_key = str(dept.parent_id) if dept.parent_id else None
            if parent_key is not None and parent_key in nodes:
                nodes[parent_key].setdefault("children", []).append(node)
            else:
                roots.append(node)
        return roots

    # ---- 用户部门归属 ----

    async def assign_user_depts(
        self, user_id: str, items: Sequence[Any]
    ) -> int:
        """覆盖式设置用户部门归属：删全部再插；空列表 = 清空归属。

        items 元素鸭子类型要求属性：dept_id / is_primary / position_id。
        校验：非空时恰一行 is_primary=true；部门存在；岗位存在（若提供）。
        返回归属行数。
        """
        user = (
            await self.session.execute(
                select(UserModel).where(UserModel.id == user_id)
            )
        ).scalar_one_or_none()
        if user is None:
            raise NotFoundError(f"用户不存在: {user_id}")

        if items:
            primary_rows = [it for it in items if it.is_primary]
            if len(primary_rows) != 1:
                raise ValidationError(
                    f"归属列表必须恰好一行 is_primary=true（当前 {len(primary_rows)} 行）"
                )
            dept_ids = {it.dept_id for it in items}
            if len(dept_ids) != len(items):
                raise ValidationError("归属列表存在重复部门")
            found = {
                str(x)
                for x in (
                    await self.session.execute(
                        select(Department.id).where(Department.id.in_(dept_ids))
                    )
                ).scalars().all()
            }
            missing = sorted(dept_ids - found)
            if missing:
                raise ValidationError(f"部门不存在: {', '.join(missing)}")
            position_ids = {it.position_id for it in items if it.position_id}
            if position_ids:
                found_positions = {
                    str(x)
                    for x in (
                        await self.session.execute(
                            select(Position.id).where(Position.id.in_(position_ids))
                        )
                    ).scalars().all()
                }
                missing_positions = sorted(position_ids - found_positions)
                if missing_positions:
                    raise ValidationError(f"岗位不存在: {', '.join(missing_positions)}")

        # 覆盖式：先删全部再插
        await self.session.execute(delete(UserDept).where(UserDept.user_id == user_id))
        for it in items:
            self.session.add(
                UserDept(
                    user_id=user_id,
                    dept_id=it.dept_id,
                    is_primary=bool(it.is_primary),
                    position_id=it.position_id,
                )
            )
        await self.session.flush()
        return len(items)
