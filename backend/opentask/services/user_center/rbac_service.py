"""RBAC 服务：角色解析、权限并集、数据范围与可见部门集（spec 3.3）

规则：
- 角色解析优先读 user_role 关联表；无行时桥接存量 user.role 字符串按
  role.code 匹配（存量用户过渡，TODO: Phase 5 管理端落地后移除桥接）；
- 权限 = 所有角色权限码的并集（role_permission → permission.code）；
- 数据范围 = 所有角色中最宽档（SCOPE_ORDER 数值最大者），无角色默认 SELF；
- 可见部门集按最宽数据范围计算：
  * ALL → None（调用方不做部门过滤）
  * DEPT_AND_CHILD → 所属部门 + department.path 前缀展开整个子树
  * DEPT → 仅用户所属部门（user_dept 表，含主/副部门）
  * CUSTOM → 角色自定义部门（role_dept）∪ 用户所属部门
  * SELF → 空集（配合 creator 条件实现"只见本人"）
- apply_data_scope 是同步的过滤注入：不查库，调用方先 await
  get_visible_dept_ids 拿到结果再传入，避免在同步上下文触发 IO。
"""
from typing import Any, ClassVar

from fastapi import HTTPException
from sqlalchemy import ColumnElement, delete, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from opentask.errors import ValidationError
from opentask.models.user_center.model import (
    Department,
    Permission,
    Role,
    RoleDept,
    RolePermission,
    UserDept,
    UserRole,
)

# update_role 的"未提供"哨兵：区分"字段不动"与"显式传值"
UNSET: Any = object()

# 合法数据范围档位
VALID_DATA_SCOPES = {"ALL", "DEPT_AND_CHILD", "DEPT", "SELF", "CUSTOM"}


class RbacService:
    """RBAC：权限并集、数据范围、可见部门集（spec 3.3）"""

    # 数据范围宽窄排序：数值越大范围越宽（CUSTOM 介于 SELF 与 DEPT 之间）
    SCOPE_ORDER: ClassVar[dict[str, int]] = {
        "ALL": 4,
        "DEPT_AND_CHILD": 3,
        "DEPT": 2,
        "CUSTOM": 1,
        "SELF": 0,
    }

    def __init__(self, session: AsyncSession):
        self.session = session

    # ---- 角色解析 ----

    async def get_user_roles(self, user) -> list[Role]:
        """解析用户角色列表。

        user_role 表有行 → 返回对应 Role 对象；
        无行 → 桥接：按 user.role 字符串查同 code 的角色
        （存量用户过渡，TODO: Phase 5 管理端落地后移除桥接）。
        """
        user_id = str(user.id)
        result = await self.session.execute(
            select(Role)
            .join(UserRole, UserRole.role_id == Role.id)
            .where(UserRole.user_id == user_id)
        )
        roles = list(result.scalars().all())
        if roles:
            return roles

        # 桥接存量单角色字符串字段
        legacy = getattr(user, "role", None)
        if not legacy:
            return []
        result = await self.session.execute(select(Role).where(Role.code == legacy))
        return list(result.scalars().all())

    async def get_user_role_codes(self, user) -> list[str]:
        """用户角色编码列表"""
        return [r.code for r in await self.get_user_roles(user)]

    async def get_user_permissions(self, user) -> set[str]:
        """用户权限码集合：所有角色的权限码并集（仅含启用权限点）"""
        roles = await self.get_user_roles(user)
        if not roles:
            return set()
        role_ids = [str(r.id) for r in roles]
        result = await self.session.execute(
            select(Permission.code)
            .join(RolePermission, RolePermission.permission_id == Permission.id)
            .where(
                RolePermission.role_id.in_(role_ids),
                Permission.status == 1,  # 停用的权限点即时失效
            )
        )
        return set(result.scalars().all())

    # ---- 数据范围 ----

    async def get_data_scope(self, user) -> str:
        """用户所有角色中最宽档（SCOPE_ORDER 最大）；无角色默认 SELF"""
        roles = await self.get_user_roles(user)
        if not roles:
            return "SELF"
        return max(
            (r.data_scope for r in roles),
            key=lambda s: self.SCOPE_ORDER.get(s, 0),
        )

    async def _get_own_dept_ids(self, user_id: str) -> set[str]:
        """用户所属部门 id 集（user_dept 表，含主/副部门）"""
        result = await self.session.execute(
            select(UserDept.dept_id).where(UserDept.user_id == user_id)
        )
        return set(result.scalars().all())

    async def get_primary_dept_id(self, user) -> str | None:
        """用户主部门 id（user_dept 中 is_primary=True 的行，一次查询）。

        业务创建链路用它写入 dept_id 归属快照；用户无部门归属时返回 None，
        行为与快照缺失的存量数据一致（列表端靠 creator 兜底或保持 NULL）。
        """
        result = await self.session.execute(
            select(UserDept.dept_id)
            .where(UserDept.user_id == str(user.id), UserDept.is_primary.is_(True))
            .limit(1)
        )
        dept_id = result.scalar_one_or_none()
        return str(dept_id) if dept_id is not None else None

    async def get_visible_dept_ids(self, user) -> set[str] | None:
        """按最宽数据范围计算可见部门 id 集。

        返回语义：
        - None → ALL，不过滤；
        - 空集 → SELF，配合 creator 条件只见本人；
        - 非空集 → 部门 id 白名单。
        """
        scope = await self.get_data_scope(user)
        if scope == "ALL":
            return None
        if scope == "SELF":
            return set()

        user_id = str(user.id)
        own_ids = await self._get_own_dept_ids(user_id)

        if scope == "DEPT":
            # 仅所属部门，不展开子树
            return own_ids

        if scope == "DEPT_AND_CHILD":
            # 所属部门 + path 前缀展开子树（path 形如 /root/a/b）
            if not own_ids:
                return set()
            result = await self.session.execute(
                select(Department.path).where(Department.id.in_(own_ids))
            )
            paths = [p for p in result.scalars().all() if p]
            if not paths:
                return set()
            # 精确前缀匹配：等于父 path 或以 "父path/" 开头
            # （直接 LIKE '父path%' 会误伤同前缀兄弟部门，如 /root 匹配 /root-x）
            subtree = or_(
                *(
                    [Department.path == p for p in paths]
                    + [Department.path.like(p + "/%") for p in paths]
                )
            )
            result = await self.session.execute(select(Department.id).where(subtree))
            # Department.id 是 UUID 类型列，统一转字符串（与 String(36) 外键一致）
            return {str(x) for x in result.scalars().all()}

        if scope == "CUSTOM":
            # 角色自定义部门（role_dept 并集）∪ 用户所属部门
            roles = await self.get_user_roles(user)
            role_ids = [str(r.id) for r in roles]
            result = await self.session.execute(
                select(RoleDept.dept_id).where(RoleDept.role_id.in_(role_ids))
            )
            return own_ids | set(result.scalars().all())

        return set()

    # ---- 过滤注入 ----

    def apply_data_scope(
        self,
        stmt: Any,
        visible_dept_ids: set[str] | None,
        dept_col: ColumnElement,
        creator_col: ColumnElement | None = None,
        user_id: str | None = None,
    ) -> Any:
        """向查询语句注入数据范围过滤（同步，不查库）。

        - visible_dept_ids is None（ALL）→ 语句原样返回；
        - creator_col 与 user_id 均提供 → or_(dept_col.in_(ids), creator_col == user_id)
          （SELF 时空部门集 + creator 条件 = 只见本人）；
        - creator_col 缺省 → dept_col.in_(ids)；SELF 时空集 → 结果恒空。
        """
        if visible_dept_ids is None:
            return stmt

        dept_filter = dept_col.in_(list(visible_dept_ids))
        if creator_col is not None and user_id is not None:
            return stmt.where(or_(dept_filter, creator_col == user_id))
        return stmt.where(dept_filter)

    # ---- 管理端 CRUD（Phase 5 Task 1）----

    async def list_roles(self) -> list[Role]:
        """全部角色（含禁用；管理端与旧角色选择器共用数据）"""
        result = await self.session.execute(select(Role).order_by(Role.code))
        return list(result.scalars().all())

    async def create_role(
        self,
        *,
        code: str,
        name: str,
        description: str | None = None,
        data_scope: str = "SELF",
    ) -> Role:
        """创建角色。code 唯一（lower 归一化判重，冲突 409），data_scope 必须是合法档位。"""
        code = (code or "").strip()
        if not code:
            raise ValidationError("角色编码不能为空")
        if data_scope not in VALID_DATA_SCOPES:
            raise ValidationError(f"非法数据范围: {data_scope}")
        # MySQL ci collation 唯一索引不区分大小写，判重统一 lower()
        # （否则 "Admin" 绕过精确等值检查、撞唯一索引变 500）
        exists = await self.session.execute(
            select(Role.id).where(func.lower(Role.code) == code.lower()).limit(1)
        )
        if exists.first() is not None:
            raise HTTPException(status_code=409, detail=f"角色编码已存在: {code}")
        role = Role(code=code, name=name, description=description, data_scope=data_scope)
        self.session.add(role)
        await self.session.flush()
        return role

    async def update_role(
        self,
        role_id: str,
        *,
        name: str | None | Any = UNSET,
        description: str | None | Any = UNSET,
        data_scope: str | None | Any = UNSET,
        dept_ids: list[str] | None = None,
    ) -> Role:
        """更新角色。

        系统角色只允许改 name/description（data_scope/dept_ids → 400）；
        data_scope=CUSTOM 时 dept_ids 覆盖 role_dept（须非空），
        切回其他档位时清空 role_dept。
        """
        role = await self._get_role(role_id)
        if name is not UNSET and name is not None:
            role.name = name
        if description is not UNSET:
            role.description = description

        scope_changed = data_scope is not UNSET and data_scope is not None
        if scope_changed:
            if data_scope not in VALID_DATA_SCOPES:
                raise ValidationError(f"非法数据范围: {data_scope}")
            if role.is_system:
                raise HTTPException(status_code=400, detail="系统角色不允许修改数据范围")
            role.data_scope = data_scope

        if dept_ids is not None:
            if role.is_system:
                raise HTTPException(status_code=400, detail="系统角色不允许配置自定义部门")
            target_scope = data_scope if scope_changed else role.data_scope
            if target_scope == "CUSTOM":
                if not dept_ids:
                    raise ValidationError("CUSTOM 数据范围必须提供至少一个部门")
                found = {
                    str(x)
                    for x in (
                        await self.session.execute(
                            select(Department.id).where(Department.id.in_(dept_ids))
                        )
                    ).scalars().all()
                }
                missing = sorted(set(dept_ids) - found)
                if missing:
                    raise ValidationError(f"部门不存在: {', '.join(missing)}")
                await self.session.execute(
                    delete(RoleDept).where(RoleDept.role_id == role_id)
                )
                for did in dept_ids:
                    self.session.add(RoleDept(role_id=role_id, dept_id=did))
            else:
                # 非 CUSTOM 档位清空历史自定义部门
                await self.session.execute(
                    delete(RoleDept).where(RoleDept.role_id == role_id)
                )

        await self.session.flush()
        return role

    async def delete_role(self, role_id: str) -> None:
        """删除角色。系统角色 → 409；仍有用户挂载 → 409。"""
        role = await self._get_role(role_id)
        if role.is_system:
            raise HTTPException(status_code=409, detail="系统预置角色不允许删除")
        role_id_str = str(role.id)
        bound = await self.session.execute(
            select(UserRole.user_id).where(UserRole.role_id == role_id_str).limit(1)
        )
        if bound.first() is not None:
            raise HTTPException(status_code=409, detail="角色下仍有用户，不能删除")
        await self.session.execute(delete(RolePermission).where(RolePermission.role_id == role_id_str))
        await self.session.execute(delete(RoleDept).where(RoleDept.role_id == role_id_str))
        await self.session.delete(role)
        await self.session.flush()

    async def set_role_permissions(self, role_id: str, codes: list[str]) -> Role:
        """整组覆盖角色权限。admin 角色 → 409（全权限不可改）；
        codes 必须全部存在且启用（否则 400）。"""
        role = await self._get_role(role_id)
        if role.code == "admin":
            raise HTTPException(status_code=409, detail="admin 角色持有全量权限，不允许修改")
        codes = list(dict.fromkeys(codes))  # 去重保序
        if codes:
            result = await self.session.execute(
                select(Permission).where(Permission.code.in_(codes))
            )
            perms = {p.code: p for p in result.scalars().all()}
            missing = sorted(set(codes) - perms.keys())
            if missing:
                raise ValidationError(f"权限码不存在: {', '.join(missing)}")
            disabled = sorted(c for c in codes if perms[c].status != 1)
            if disabled:
                raise ValidationError(f"权限点已停用，不能分配: {', '.join(disabled)}")
            desired = {str(perms[c].id) for c in codes}
        else:
            desired = set()

        await self.session.execute(
            delete(RolePermission).where(RolePermission.role_id == str(role.id))
        )
        for perm_id in desired:
            self.session.add(RolePermission(role_id=str(role.id), permission_id=perm_id))
        await self.session.flush()
        return role

    async def list_role_permission_codes(self, role_id: str) -> list[str]:
        """角色当前权限码列表（管理端回显勾选集；admin 角色由 seed 播全量）"""
        role = await self._get_role(role_id)
        result = await self.session.execute(
            select(Permission.code)
            .join(RolePermission, RolePermission.permission_id == Permission.id)
            .where(RolePermission.role_id == str(role.id))
            .order_by(Permission.code)
        )
        return list(result.scalars().all())

    async def list_role_dept_ids(self, role_id: str) -> list[str]:
        """角色 CUSTOM 数据范围的自定义部门 id 列表（管理端回显）"""
        role = await self._get_role(role_id)
        result = await self.session.execute(
            select(RoleDept.dept_id).where(RoleDept.role_id == str(role.id))
        )
        return list(result.scalars().all())

    async def list_permissions(self) -> list[Permission]:
        """全部权限点（含停用；module 分组由前端做）"""
        result = await self.session.execute(
            select(Permission).order_by(Permission.code)
        )
        return list(result.scalars().all())

    async def set_permission_status(self, permission_id: str, status: int) -> Permission:
        """启用/停用权限点（停用后 require_permission 即时 403）"""
        if status not in (0, 1):
            raise ValidationError("status 仅允许 0（停用）或 1（启用）")
        result = await self.session.execute(
            select(Permission).where(Permission.id == permission_id)
        )
        perm = result.scalar_one_or_none()
        if perm is None:
            raise HTTPException(status_code=404, detail="权限点不存在")
        perm.status = status
        await self.session.flush()
        return perm

    async def _get_role(self, role_id: str) -> Role:
        """按 id 查角色，不存在抛 404"""
        result = await self.session.execute(select(Role).where(Role.id == role_id))
        role = result.scalar_one_or_none()
        if role is None:
            raise HTTPException(status_code=404, detail="角色不存在")
        return role
