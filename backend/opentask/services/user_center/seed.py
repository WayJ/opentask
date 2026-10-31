"""用户中心幂等播种：权限点字典 + 系统角色

规则：
- permission：按 code upsert（存在则更新 name/type/route_key，不存在插入）；
  字典中移除的权限码不删除 permission 行（管理端可读历史），只从系统角色的
  role_permission 中清除（否则停用权限不生效）；
- 系统角色 4 个（is_system=True）：admin / maintainer / developer / viewer，
  role_permission 同步为该角色的目标权限集（缺则补、多则删）；
- 幂等：连跑多遍结果一致；提交策略与 user_sync_service 保持一致（commit）。
"""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from opentask.models.user_center import Permission, Role, RolePermission
from opentask.services.user_center.permission_defs import PERMISSIONS

# 业务模块前缀（权限码形如 {module}:{op}）
_BUSINESS_MODULES = ("requirement", "issue", "project", "knowledge", "task")


def _business_codes(*ops: str) -> set[str]:
    """生成业务模块权限码集合，如 _business_codes("view", "create")"""
    return {f"{m}:{op}" for m in _BUSINESS_MODULES for op in ops}


def _system_role_defs() -> list[dict]:
    """系统角色定义（code/name/data_scope/目标权限码集合）"""
    return [
        {
            "code": "admin",
            "name": "系统管理员",
            "data_scope": "ALL",
            "perms": {p["code"] for p in PERMISSIONS},
        },
        {
            "code": "maintainer",
            "name": "维护者",
            "data_scope": "ALL",
            "perms": _business_codes("view", "create", "update", "delete")
            | {"menu:manage_user", "manage:user:status", "manage:user:role"},
        },
        {
            "code": "developer",
            "name": "开发者",
            "data_scope": "DEPT_AND_CHILD",
            "perms": _business_codes("view", "create", "update"),
        },
        {
            "code": "viewer",
            "name": "查看者",
            "data_scope": "SELF",
            "perms": _business_codes("view"),
        },
    ]


async def seed_user_center(session: AsyncSession) -> dict:
    """幂等播种权限点与系统角色。

    Returns:
        {"permissions": n, "roles": n}——播种后库内权限点与系统角色总数。
    """
    # ---- 1. 权限点 upsert ----
    dict_codes = {p["code"] for p in PERMISSIONS}
    result = await session.execute(select(Permission))
    perm_by_code = {p.code: p for p in result.scalars().all()}

    for item in PERMISSIONS:
        perm = perm_by_code.get(item["code"])
        if perm is None:
            perm = Permission(
                code=item["code"],
                name=item["name"],
                type=item["type"],
                route_key=item["route_key"],
            )
            session.add(perm)
            perm_by_code[perm.code] = perm
        else:
            # 字典可演进：名称/类型/路由以代码为准
            perm.name = item["name"]
            perm.type = item["type"]
            perm.route_key = item["route_key"]

    await session.flush()  # 生成新权限点 id

    # ---- 2. 系统角色 upsert ----
    role_defs = _system_role_defs()
    result = await session.execute(select(Role).where(Role.code.in_([d["code"] for d in role_defs])))
    role_by_code = {r.code: r for r in result.scalars().all()}

    for d in role_defs:
        role = role_by_code.get(d["code"])
        if role is None:
            role = Role(
                code=d["code"],
                name=d["name"],
                data_scope=d["data_scope"],
                is_system=True,
            )
            session.add(role)
            role_by_code[role.code] = role
        else:
            role.name = d["name"]
            role.data_scope = d["data_scope"]
            role.is_system = True

    await session.flush()  # 生成新角色 id

    # ---- 3. 同步 role_permission（缺则补、多则删）----
    for d in role_defs:
        role = role_by_code[d["code"]]
        # role_id/permission_id 为 String(36)，id 是 UUID 对象，统一转字符串
        role_id = str(role.id)
        desired = {
            str(perm_by_code[c].id) for c in d["perms"] if c in perm_by_code and c in dict_codes
        }

        result = await session.execute(
            select(RolePermission).where(RolePermission.role_id == role_id)
        )
        current = {rp.permission_id: rp for rp in result.scalars().all()}

        # 补缺
        for perm_id in desired - current.keys():
            session.add(RolePermission(role_id=role_id, permission_id=perm_id))
        # 删多（含字典中已移除的权限码，否则停用权限不生效）
        for perm_id, rp in current.items():
            if perm_id not in desired:
                await session.delete(rp)

    await session.flush()

    # ---- 4. 统计并提交（与 user_sync_service 的提交风格一致）----
    perm_count = len((await session.execute(select(Permission.id))).all())
    role_count = len(
        (await session.execute(select(Role.id).where(Role.is_system.is_(True)))).all()
    )
    await session.commit()

    return {"permissions": perm_count, "roles": role_count}
