"""角色管理 API（Phase 5 Task 1）

- GET /api/roles：登录即可。响应 data 兼容旧结构
  [{value: code, label: name, description, ...}]（fetchGetRoles 消费），
  并补充 id / data_scope / is_system / status 供管理端使用；
- 写操作：manage:role:create / manage:role:update / manage:role:delete /
  manage:role:perm（PUT /{id}/permissions 整组覆盖角色权限）。

DB 操作全部委托 RbacService（services 层）。
"""
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from opentask.api.user_center.deps import require_permission
from opentask.auth import authenticate
from opentask.models.user.model import UserModel
from opentask.repositories.base import get_session
from opentask.services.user_center.rbac_service import RbacService

router = APIRouter(prefix="/api/roles", tags=["角色管理"])


class RoleCreate(BaseModel):
    """创建角色请求体"""

    code: str = Field(min_length=1, max_length=50)
    name: str = Field(min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=255)
    data_scope: str = "SELF"


class RoleUpdate(BaseModel):
    """更新角色请求体（未提供的字段不动；系统角色只许改 name/description）"""

    name: str | None = Field(default=None, min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=255)
    data_scope: str | None = None
    dept_ids: list[str] | None = None


class RolePermissionsUpdate(BaseModel):
    """整组覆盖角色权限请求体"""

    codes: list[str] = Field(default_factory=list)


def _role_data(role) -> dict:
    """角色 ORM → 兼容旧结构的响应 dict（value/label 供 fetchGetRoles 消费）"""
    return {
        "id": str(role.id),
        "value": role.code,
        "label": role.name,
        "description": role.description or "",
        "code": role.code,
        "name": role.name,
        "data_scope": role.data_scope,
        "is_system": bool(role.is_system),
        "status": role.status,
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
async def list_roles(
    current_user: UserModel = Depends(authenticate),
    session=Depends(get_session),
) -> dict:
    """角色列表（登录即可；含系统角色与禁用角色）"""
    roles = await RbacService(session).list_roles()
    return _ok([_role_data(r) for r in roles])


@router.post("")
async def create_role(
    payload: RoleCreate,
    current_user: UserModel = require_permission("manage:role:create"),
    session=Depends(get_session),
) -> dict:
    """创建角色（code 唯一，冲突 409）"""
    role = await RbacService(session).create_role(
        code=payload.code,
        name=payload.name,
        description=payload.description,
        data_scope=payload.data_scope,
    )
    return _ok(_role_data(role))


@router.put("/{role_id}")
async def update_role(
    role_id: str,
    payload: RoleUpdate,
    current_user: UserModel = require_permission("manage:role:update"),
    session=Depends(get_session),
) -> dict:
    """更新角色（系统角色只许改 name/description；CUSTOM 范围由 dept_ids 覆盖）"""
    kwargs: dict[str, Any] = {}
    if "name" in payload.model_fields_set:
        kwargs["name"] = payload.name
    if "description" in payload.model_fields_set:
        kwargs["description"] = payload.description
    if "data_scope" in payload.model_fields_set:
        kwargs["data_scope"] = payload.data_scope
    if "dept_ids" in payload.model_fields_set:
        kwargs["dept_ids"] = payload.dept_ids
    role = await RbacService(session).update_role(role_id, **kwargs)
    return _ok(_role_data(role))


@router.delete("/{role_id}")
async def delete_role(
    role_id: str,
    current_user: UserModel = require_permission("manage:role:delete"),
    session=Depends(get_session),
) -> dict:
    """删除角色（系统角色 409；仍有关联用户 409）"""
    await RbacService(session).delete_role(role_id)
    return _ok(message="deleted")


@router.get("/{role_id}/permissions")
async def get_role_permissions(
    role_id: str,
    current_user: UserModel = Depends(authenticate),
    session=Depends(get_session),
) -> dict:
    """角色当前权限码集合（登录即可读；管理端权限勾选回显）。

    data 同时携带 dept_ids（CUSTOM 数据范围的自定义部门回显），
    避免管理端为编辑数据范围再发一次请求。
    """
    svc = RbacService(session)
    codes = await svc.list_role_permission_codes(role_id)
    dept_ids = await svc.list_role_dept_ids(role_id)
    return _ok({"codes": codes, "dept_ids": dept_ids})


@router.put("/{role_id}/permissions")
async def set_role_permissions(
    role_id: str,
    payload: RolePermissionsUpdate,
    current_user: UserModel = require_permission("manage:role:perm"),
    session=Depends(get_session),
) -> dict:
    """整组覆盖角色权限（codes 必须全部存在且启用；admin 角色 409）"""
    role = await RbacService(session).set_role_permissions(role_id, payload.codes)
    return _ok(_role_data(role))
