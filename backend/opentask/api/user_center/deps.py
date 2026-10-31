"""权限依赖工厂：require_permission(code) → FastAPI Depends（spec 5.7）

用法：路由参数直接以 require_permission(...) 为默认值（返回值即 Depends 实例）：

    current_user: UserModel = require_permission("manage:user:status")

规则：
- 权限集由 RbacService 计算（user_role 优先，存量 user.role 字符串桥接）；
- 请求级缓存（request.state._perm_cache）：同一请求挂多个权限依赖只查一次库；
- "*" 通配全放行——当前 seed 的 admin 为全量具体权限码（非 "*"），
  通配仅作超管角色的防御性保留，无副作用。
"""
from fastapi import Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from opentask.auth import authenticate
from opentask.models.user.model import UserModel
from opentask.repositories.base import get_session
from opentask.services.user_center.rbac_service import RbacService


def require_permission(code: str):
    """构造要求指定权限码的 FastAPI 依赖（返回 Depends 实例）"""

    async def _checker(
        request: Request,
        current_user: UserModel = Depends(authenticate),
        session: AsyncSession = Depends(get_session),
    ) -> UserModel:
        # 请求级缓存：同一请求多个 require_permission 不重复查权限
        cached = getattr(request.state, "_perm_cache", None)
        if cached is None:
            rbac = RbacService(session)
            cached = await rbac.get_user_permissions(current_user)
            request.state._perm_cache = cached
        # admin 通配（"*" 在权限集 → 全放行）
        if "*" in cached or code in cached:
            return current_user
        raise HTTPException(status_code=403, detail="权限不足")

    return Depends(_checker)
