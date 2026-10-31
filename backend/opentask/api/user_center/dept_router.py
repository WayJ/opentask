"""部门管理 API：部门树查询 / CRUD / 启禁 + 用户部门归属分配

权限：
- GET /api/departments：登录即可（树是管理端与选择器共用数据）；
- 部门写操作：manage:dept:create / manage:dept:update / manage:dept:delete
  （无独立 status 权限码，启禁用复用 manage:dept:update）；
- 用户归属分配：manage:user:update。

响应统一 {code, message, data, timestamp} 包装（与 user_center/router.py 一致）。
"""
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from opentask.api.user_center.deps import require_permission
from opentask.auth import authenticate
from opentask.models.user.model import UserModel
from opentask.repositories.base import get_session
from opentask.services.user_center.dept_service import DeptService

router = APIRouter(prefix="/api", tags=["部门管理"])


class DeptCreate(BaseModel):
    """创建部门请求体"""

    name: str = Field(min_length=1, max_length=100)
    parent_id: str | None = None
    sort: int = 0


class DeptUpdate(BaseModel):
    """更新部门请求体（PUT；未提供的字段不动，显式 null 的 parent_id = 移为根）"""

    name: str | None = Field(default=None, min_length=1, max_length=100)
    parent_id: str | None = None
    sort: int | None = None


class DeptStatusUpdate(BaseModel):
    """启禁用部门请求体"""

    status: int  # 1 启用 0 禁用


class UserDeptItem(BaseModel):
    """用户单个部门归属行"""

    dept_id: str
    is_primary: bool = False
    position_id: str | None = None


class UserDeptAssign(BaseModel):
    """用户部门归属分配请求体（覆盖式；空数组 = 清空归属）"""

    items: list[UserDeptItem] = Field(default_factory=list)


def _dept_data(dept) -> dict:
    """部门 ORM → 响应 dict（id 统一 36 位字符串）"""
    return {
        "id": str(dept.id),
        "name": dept.name,
        "parent_id": str(dept.parent_id) if dept.parent_id else None,
        "path": dept.path,
        "sort": dept.sort,
        "status": dept.status,
    }


def _ok(data: Any = None, message: str = "success") -> dict:
    """统一响应包装"""
    return {
        "code": 200,
        "message": message,
        "data": data,
        "timestamp": int(datetime.now().timestamp() * 1000),
    }


@router.get("/departments")
async def get_dept_tree(
    current_user: UserModel = Depends(authenticate),
    session=Depends(get_session),
) -> dict:
    """部门树（children 嵌套；登录即可）"""
    tree = await DeptService(session).get_tree()
    return _ok(tree)


@router.post("/departments")
async def create_dept(
    payload: DeptCreate,
    current_user: UserModel = require_permission("manage:dept:create"),
    session=Depends(get_session),
) -> dict:
    """创建部门（parent_id 空 = 根部门）"""
    dept = await DeptService(session).create_dept(
        name=payload.name, parent_id=payload.parent_id, sort=payload.sort
    )
    return _ok(_dept_data(dept))


@router.put("/departments/{dept_id}")
async def update_dept(
    dept_id: str,
    payload: DeptUpdate,
    current_user: UserModel = require_permission("manage:dept:update"),
    session=Depends(get_session),
) -> dict:
    """更新部门（name/sort/移动；移动时后端重算整棵子树 path）"""
    kwargs: dict[str, Any] = {}
    # model_fields_set 区分"未提供"与"显式 null"（parent_id=null = 移为根）
    if "name" in payload.model_fields_set:
        kwargs["name"] = payload.name
    if "sort" in payload.model_fields_set:
        kwargs["sort"] = payload.sort
    if "parent_id" in payload.model_fields_set:
        kwargs["parent_id"] = payload.parent_id
    dept = await DeptService(session).update_dept(dept_id, **kwargs)
    return _ok(_dept_data(dept))


@router.put("/departments/{dept_id}/status")
async def set_dept_status(
    dept_id: str,
    payload: DeptStatusUpdate,
    current_user: UserModel = require_permission("manage:dept:update"),
    session=Depends(get_session),
) -> dict:
    """启用/禁用部门（无独立 status 权限码，复用 manage:dept:update）"""
    dept = await DeptService(session).set_dept_status(dept_id, payload.status)
    return _ok(_dept_data(dept))


@router.delete("/departments/{dept_id}")
async def delete_dept(
    dept_id: str,
    current_user: UserModel = require_permission("manage:dept:delete"),
    session=Depends(get_session),
) -> dict:
    """删除部门（有子部门或有成员 → 409）"""
    await DeptService(session).delete_dept(dept_id)
    return _ok(message="deleted")


@router.put("/users/{user_id}/depts")
async def assign_user_depts(
    user_id: str,
    payload: UserDeptAssign,
    current_user: UserModel = require_permission("manage:user:update"),
    session=Depends(get_session),
) -> dict:
    """覆盖式设置用户部门归属（空数组 = 清空归属）"""
    count = await DeptService(session).assign_user_depts(user_id, payload.items)
    return _ok({"assigned": count})
