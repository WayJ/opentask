"""权限点管理 API（Phase 5 Task 1）

- GET /api/permissions：登录即可，全量权限点列表
  （module 分组、menu/button 分级由前端基于 code/type 自行处理）；
- PUT /api/permissions/{id}/status：权限点启停，manage:role:perm 权限。
  停用后 get_user_permissions 即时剔除该码（status==1 过滤），
  require_permission 对所有依赖该码的端点立即 403。

DB 操作全部委托 RbacService（services 层）。
"""
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from opentask.api.user_center.deps import require_permission
from opentask.auth import authenticate
from opentask.models.user.model import UserModel
from opentask.repositories.base import get_session
from opentask.services.user_center.rbac_service import RbacService

router = APIRouter(prefix="/api/permissions", tags=["权限点管理"])


class PermissionStatusUpdate(BaseModel):
    """权限点启停请求体"""

    status: int  # 1 启用 0 停用


def _perm_data(perm) -> dict:
    """权限点 ORM → 响应 dict"""
    return {
        "id": str(perm.id),
        "code": perm.code,
        "name": perm.name,
        "type": perm.type,
        "route_key": perm.route_key,
        "status": perm.status,
    }


def _ok(data: Any = None, message: str = "success") -> dict:
    """统一响应包装"""
    return {
        "code": 200,
        "message": message,
        "data": data,
        "timestamp": int(datetime.now().timestamp() * 1000),
    }


@router.get("")
async def list_permissions(
    current_user: UserModel = Depends(authenticate),
    session=Depends(get_session),
) -> dict:
    """权限点列表（登录即可，含停用权限点）"""
    perms = await RbacService(session).list_permissions()
    return _ok([_perm_data(p) for p in perms])


@router.put("/{permission_id}/status")
async def set_permission_status(
    permission_id: str,
    payload: PermissionStatusUpdate,
    current_user: UserModel = require_permission("manage:role:perm"),
    session=Depends(get_session),
) -> dict:
    """启用/停用权限点（停用后 require_permission 即时 403）"""
    perm = await RbacService(session).set_permission_status(permission_id, payload.status)
    return _ok(_perm_data(perm))
