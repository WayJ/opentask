"""
用户管理 API

提供用户列表、用户状态管理、角色管理等功能
权限由 require_permission 依赖按权限码控制（RBAC，spec 5.7）
"""
import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from passlib.context import CryptContext
from pydantic import BaseModel, Field
from sqlalchemy import select, func, or_, and_, delete, update
from sqlalchemy.ext.asyncio import AsyncSession

from opentask.config import config
from opentask.auth import authenticate
from opentask.api.user_center.deps import require_permission
from opentask.repositories.base import get_session
from opentask.services.user_center.dept_service import DeptService
from opentask.services.user_center.rbac_service import RbacService
from opentask.services.user_center.token_service import TokenService
from opentask.services.user_center.utils import generate_temp_password
from opentask.models.user.model import UserModel
from opentask.models.user.schema import (
    CurrentUserResponse,
    UserListItem,
    UserSearchParams,
    UserStatusUpdate,
    UserRoleUpdate,
)
from opentask.models.user_center.model import Role, UserDept, UserRole

logger = logging.getLogger(__name__)

# 密码哈希上下文（bcrypt），与 auth_service 保持一致
_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# 创建 router，使用配置的 API 前缀
router = APIRouter(prefix="/api/users", tags=["用户管理"])


@router.get("/me", response_model=dict)
async def get_current_user(
    current_user: UserModel = Depends(authenticate),
    session: AsyncSession = Depends(get_session),
    x_workspace_id: str | None = Header(None, alias="X-Workspace-Id"),
) -> dict:
    """获取当前登录用户信息（含当前工作区角色）。"""
    permissions = sorted(await RbacService(session).get_user_permissions(current_user))
    workspace_role = None
    if x_workspace_id:
        from opentask.services.workspace.service import WorkspaceService

        member = await WorkspaceService(session).get_membership(
            x_workspace_id, str(current_user.id)
        )
        if member is not None:
            workspace_role = member.role

    return {
        "code": 200,
        "message": "success",
        "data": CurrentUserResponse(
            id=str(current_user.id),
            sso_user_id=current_user.sso_user_id,
            dingtalk_user_id=current_user.dingtalk_user_id,
            sso_account=current_user.sso_account,
            sso_name=current_user.sso_name,
            organize_name=current_user.organize_name,
            position_name=current_user.position_name,
            role=current_user.role,
            workspace_role=workspace_role,
            status=current_user.status,
            permissions=permissions,
        ).model_dump(by_alias=True),
        "timestamp": int(datetime.now().timestamp() * 1000)
    }


@router.get("/searchable", response_model=dict)
async def get_searchable_users(
    keyword: Optional[str] = Query(None, max_length=100, description="搜索关键字"),
    current_user: UserModel = Depends(authenticate),
    session: AsyncSession = Depends(get_session),
) -> dict:
    """
    获取可搜索的用户列表（用于选择负责人等场景）

    任何已登录用户都可以访问，返回简化的用户信息
    只返回启用状态的用户

    Returns:
        {
            "code": 200,
            "message": "success",
            "data": [
                {
                    "id": "xxx",
                    "sso_account": "laker",
                    "sso_name": "张三",
                    ...
                }
            ],
            "timestamp": 1234567890
        }
    """
    # 构建查询：只返回启用状态的用户
    query = select(UserModel).where(UserModel.status == 1)

    # 应用关键字搜索
    if keyword and keyword.strip():
        query = query.where(
            or_(
                UserModel.sso_account.ilike(f"%{keyword}%"),
                UserModel.sso_name.ilike(f"%{keyword}%"),
            )
        )

    # 按账号排序
    query = query.order_by(UserModel.sso_account.asc())

    # 限制返回数量（最多返回100个用户）
    query = query.limit(100)

    result = await session.execute(query)
    users = result.scalars().all()

    # 转换为简化的响应格式
    user_list = [
        {
            "id": str(user.id),
            "sso_user_id": user.sso_user_id,
            "sso_account": user.sso_account,
            "sso_name": user.sso_name,
        }
        for user in users
    ]

    return {
        "code": 200,
        "message": "success",
        "data": user_list,
        "timestamp": int(datetime.now().timestamp() * 1000)
    }


@router.get("", response_model=dict)
async def get_users(
    current: int = Query(1, ge=1, description="当前页码"),
    pageSize: int = Query(10, ge=1, le=100, description="每页大小"),
    status: Optional[str] = Query(None, description="用户状态筛选"),
    keyword: Optional[str] = Query(None, max_length=100, description="关键字搜索"),
    role: Optional[str] = Query(None, description="角色筛选"),
    dept_id: Optional[str] = Query(None, description="部门筛选（user_dept join）"),
    current_user: UserModel = require_permission("menu:manage_user"),
    session: AsyncSession = Depends(get_session),
) -> dict:
    """
    获取用户列表（分页）

    需要 menu:manage_user 权限；
    角色筛选用 user_role join（无 user_role 行的存量用户回退 role 字符串桥接）。
    """
    # 处理status参数：将空字符串转换为None，将字符串转换为int
    status_int = None
    if status and status.strip():
        try:
            status_int = int(status)
            if status_int not in [0, 1]:
                raise HTTPException(status_code=400, detail="status必须是0或1")
        except ValueError:
            raise HTTPException(status_code=400, detail="status必须是整数")

    # 构建查询
    query = select(UserModel)

    # 应用筛选条件
    if status_int is not None:
        query = query.where(UserModel.status == status_int)

    if role:
        # user_role join 优先；无关联行的存量用户回退 role 字符串（桥接兼容）
        via_user_role = UserModel.id.in_(
            select(UserRole.user_id)
            .join(Role, Role.id == UserRole.role_id)
            .where(Role.code == role)
        )
        via_legacy = and_(
            ~UserModel.id.in_(select(UserRole.user_id)),
            UserModel.role == role,
        )
        query = query.where(or_(via_user_role, via_legacy))

    if dept_id:
        query = query.where(
            UserModel.id.in_(
                select(UserDept.user_id).where(UserDept.dept_id == dept_id)
            )
        )

    if keyword:
        query = query.where(
            or_(
                UserModel.sso_account.ilike(f"%{keyword}%"),
                UserModel.sso_name.ilike(f"%{keyword}%"),
            )
        )

    # 获取总数
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await session.execute(count_query)
    total = total_result.scalar() or 0

    # 分页查询 - 按创建时间倒序排序
    query = query.order_by(UserModel.created_at.desc())
    query = query.offset((current - 1) * pageSize).limit(pageSize)

    result = await session.execute(query)
    users = result.scalars().all()

    # 批量拉取本页用户的角色编码（user_role join；无行的存量用户回退 role 字符串）
    user_ids = [str(u.id) for u in users]
    role_codes_map: dict[str, list[str]] = {}
    if user_ids:
        roles_result = await session.execute(
            select(UserRole.user_id, Role.code)
            .join(Role, Role.id == UserRole.role_id)
            .where(UserRole.user_id.in_(user_ids))
        )
        for uid, code in roles_result.all():
            role_codes_map.setdefault(uid, []).append(code)

    # 转换为响应格式
    rows = [
            UserListItem(
                id=str(user.id),
                username=user.username,
                name=user.name,
                sso_user_id=user.sso_user_id,
                sso_account=user.sso_account,
                sso_name=user.sso_name,
                organize_name=user.organize_name,
                position_name=user.position_name,
                role=user.role,
                role_codes=role_codes_map.get(str(user.id))
                or ([user.role] if user.role else []),
                status=user.status,
                last_login_time=user.last_login_time,
                sync_time=user.sync_time,
                created_at=user.created_at,
            ).model_dump(by_alias=True)
            for user in users
    ]

    total_pages = (total + pageSize - 1) // pageSize

    return {
        "code": 200,
        "message": "success",
        "data": {
            "rows": rows,
            "total": total,
            "current": current,
            "pageSize": pageSize,
            "totalPages": total_pages,
        },
        "timestamp": int(datetime.now().timestamp() * 1000)
    }


@router.put("/{user_id}/status", response_model=dict)
async def update_user_status(
    user_id: str,
    status_update: UserStatusUpdate,
    current_user: UserModel = require_permission("manage:user:status"),
    session: AsyncSession = Depends(get_session),
) -> dict:
    """
    更新用户状态（启用/禁用）

    需要 manage:user:status 权限；
    禁用（status=0）时同步 token_version+1（旧 access 全失效）
    并吊销该用户全部 refresh token（禁用即全端下线，参照软删/重置密码写法）。
    """
    # 查找用户
    result = await session.execute(
        select(UserModel).where(UserModel.id == user_id)
    )
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    # 更新状态；禁用时 SQL 原子自增 token_version（ORM 读改写会丢并发 +1）
    values: dict = {"status": status_update.status}
    if status_update.status == 0:
        values["token_version"] = func.coalesce(UserModel.token_version, 0) + 1
    await session.execute(update(UserModel).where(UserModel.id == user_id).values(**values))
    await session.commit()

    # 吊销该用户全部 refresh token（含内部 commit）
    if status_update.status == 0:
        await TokenService(session).revoke_all_user_refresh(str(user.id))

    logger.info(f"用户状态更新: {user.sso_account} -> {status_update.status} (操作者: {current_user.sso_account})")

    return {
        "code": 200,
        "message": "用户状态更新成功",
        "data": None,
        "timestamp": int(datetime.now().timestamp() * 1000)
    }


@router.put("/{user_id}/role", response_model=dict)
async def update_user_role(
    user_id: str,
    role_update: UserRoleUpdate,
    current_user: UserModel = require_permission("manage:user:role"),
    session: AsyncSession = Depends(get_session),
) -> dict:
    """
    更新用户角色

    需要 manage:user:role 权限
    """
    # 验证角色值
    valid_roles = ["admin", "maintainer", "developer", "viewer"]
    if role_update.role not in valid_roles:
        raise HTTPException(status_code=400, detail=f"无效的角色值，必须是: {', '.join(valid_roles)}")

    # 查找用户
    result = await session.execute(
        select(UserModel).where(UserModel.id == user_id)
    )
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    # 防止用户修改自己的角色
    if user.id == current_user.id:
        raise HTTPException(status_code=400, detail="不能修改自己的角色")

    # 不允许修改 admin 角色的用户
    if user.role == "admin":
        raise HTTPException(status_code=403, detail="不能修改管理员的角色")

    # 更新角色
    old_role = user.role
    user.role = role_update.role
    await session.commit()

    logger.info(f"用户角色更新: {user.sso_account} {old_role} -> {role_update.role} (操作者: {current_user.sso_account})")

    return {
        "code": 200,
        "message": "用户角色更新成功",
        "data": None,
        "timestamp": int(datetime.now().timestamp() * 1000)
    }


# ============================================================================
# 管理端用户 CRUD（Phase 5 Task 1）
# ============================================================================


class DeptAssignmentItem(BaseModel):
    """用户部门归属行（校验逻辑复用 DeptService.assign_user_depts）"""

    dept_id: str
    is_primary: bool = False
    position_id: str | None = None


class UserCreateIn(BaseModel):
    """创建用户请求体

    password 可选：空/缺省 → 不写 hash 且 must_change_password=True
    （用户无法本地登录，待管理员重置密码）。
    """

    username: str = Field(min_length=1, max_length=50)
    name: str = Field(min_length=1, max_length=100)
    role_codes: list[str] = Field(default_factory=list)
    dept_assignments: list[DeptAssignmentItem] = Field(default_factory=list)
    password: str | None = Field(default=None, max_length=128)


class UserUpdateIn(BaseModel):
    """编辑用户请求体（username 是唯一标识，不允许修改）"""

    name: str | None = Field(default=None, min_length=1, max_length=100)
    role_codes: list[str] | None = None
    dept_assignments: list[DeptAssignmentItem] | None = None


async def _get_user_or_404(session: AsyncSession, user_id: str) -> UserModel:
    result = await session.execute(select(UserModel).where(UserModel.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    return user


async def _apply_role_codes(session: AsyncSession, user: UserModel, role_codes: list[str]) -> None:
    """桥接双写：user_role 表覆盖式写 + user.role 存量字符串同步为第一个角色 code。

    空列表 → 清空 user_role 行并置 role 字符串为空串
    （role 列 NOT NULL 不能置 None；空串在 get_user_roles/getUserInfo 的
    桥接分支中均为 falsy → 无角色、默认 SELF 无权限）。
    """
    result = await session.execute(select(Role).where(Role.code.in_(role_codes)))
    roles = {r.code: r for r in result.scalars().all()}
    missing = sorted(set(role_codes) - roles.keys())
    if missing:
        raise HTTPException(status_code=400, detail=f"角色不存在: {', '.join(missing)}")

    user_id = str(user.id)
    await session.execute(delete(UserRole).where(UserRole.user_id == user_id))
    for code in role_codes:
        session.add(UserRole(user_id=user_id, role_id=str(roles[code].id)))
    # 存量 role 字符串同步（桥接期间展示/筛选兼容）；空列表清空，避免
    # "user_role 已清但 role 字符串残留" 导致桥接回退继续按旧角色授权
    user.role = role_codes[0] if role_codes else ""


@router.post("", response_model=dict)
async def create_user(
    payload: UserCreateIn,
    current_user: UserModel = require_permission("manage:user:create"),
    session: AsyncSession = Depends(get_session),
) -> dict:
    """
    创建用户（管理端）

    需要 manage:user:create 权限；
    username 唯一（lower 归一化判重，冲突 409）；
    密码可选：空 → 无 hash + must_change_password=True；
    角色桥接双写（user_role 行 + user.role 字符串）。
    """
    username = payload.username.strip()
    # MySQL ci collation 唯一索引不区分大小写，判重统一 lower()
    dup = await session.execute(
        select(UserModel.id).where(func.lower(UserModel.username) == username.lower()).limit(1)
    )
    if dup.first() is not None:
        raise HTTPException(status_code=409, detail=f"用户名已存在: {username}")

    password = (payload.password or "").strip()
    user = UserModel(
        name=payload.name,
        username=username,
        password_hash=_pwd_context.hash(password) if password else None,
        must_change_password=not password,
        # 空角色列表 → 空串（NOT NULL 列，桥接分支视为无角色，默认 SELF 无权限）
        role=payload.role_codes[0] if payload.role_codes else "",
        status=1,
    )
    session.add(user)
    await session.flush()

    await _apply_role_codes(session, user, payload.role_codes)
    if payload.dept_assignments:
        await DeptService(session).assign_user_depts(str(user.id), payload.dept_assignments)
    await session.commit()

    logger.info(f"管理端创建用户: {username} (操作者: {current_user.username or current_user.id})")
    return {
        "code": 200,
        "message": "创建成功",
        "data": {
            "id": str(user.id),
            "username": user.username,
            "name": user.name,
            "role": user.role,
            "must_change_password": user.must_change_password,
        },
        "timestamp": int(datetime.now().timestamp() * 1000),
    }


@router.get("/{user_id}", response_model=dict)
async def get_user_detail(
    user_id: str,
    current_user: UserModel = require_permission("menu:manage_user"),
    session: AsyncSession = Depends(get_session),
) -> dict:
    """
    用户详情（管理端编辑抽屉回显用）

    需要 menu:manage_user 权限；
    返回 name/username/status/role_codes/dept_assignments（含 is_primary）
    供 PUT /{user_id} 全量覆盖式编辑前回显。
    """
    user = await _get_user_or_404(session, user_id)
    rbac = RbacService(session)
    role_codes = await rbac.get_user_role_codes(user)

    dept_result = await session.execute(
        select(UserDept).where(UserDept.user_id == user_id)
    )
    dept_assignments = [
        {"dept_id": str(row.dept_id), "is_primary": bool(row.is_primary), "position_id": row.position_id}
        for row in dept_result.scalars().all()
    ]

    return {
        "code": 200,
        "message": "success",
        "data": {
            "id": str(user.id),
            "username": user.username,
            "name": user.name,
            "sso_account": user.sso_account,
            "sso_name": user.sso_name,
            "role": user.role,
            "role_codes": role_codes,
            "dept_assignments": dept_assignments,
            "status": user.status,
            "last_login_time": user.last_login_time,
        },
        "timestamp": int(datetime.now().timestamp() * 1000),
    }


@router.put("/{user_id}", response_model=dict)
async def update_user(
    user_id: str,
    payload: UserUpdateIn,
    current_user: UserModel = require_permission("manage:user:update"),
    session: AsyncSession = Depends(get_session),
) -> dict:
    """
    编辑用户（管理端；username 为唯一标识不可修改）

    需要 manage:user:update 权限；
    role_codes 提供时桥接双写（user_role 覆盖 + user.role 同步第一个角色）。
    """
    user = await _get_user_or_404(session, user_id)

    if payload.name is not None:
        user.name = payload.name
    if payload.role_codes is not None:
        await _apply_role_codes(session, user, payload.role_codes)
    if payload.dept_assignments is not None:
        await DeptService(session).assign_user_depts(user_id, payload.dept_assignments)
    await session.commit()

    logger.info(f"管理端编辑用户: {user.username} (操作者: {current_user.username or current_user.id})")
    return {
        "code": 200,
        "message": "更新成功",
        "data": {
            "id": str(user.id),
            "username": user.username,
            "name": user.name,
            "role": user.role,
        },
        "timestamp": int(datetime.now().timestamp() * 1000),
    }


@router.delete("/{user_id}", response_model=dict)
async def delete_user(
    user_id: str,
    current_user: UserModel = require_permission("manage:user:delete"),
    session: AsyncSession = Depends(get_session),
) -> dict:
    """
    软禁用用户（status=0 + token_version+1 + 吊销全部 refresh）

    需要 manage:user:delete 权限；已是禁用状态 → 409。
    旧 access JWT 因 token_version 变化立即失效（authenticate 校验 tv）。
    """
    user = await _get_user_or_404(session, user_id)
    if user.status == 0:
        raise HTTPException(status_code=409, detail="用户已是禁用状态")

    user.status = 0
    user.token_version = (user.token_version or 0) + 1
    await session.commit()
    # 吊销该用户全部 refresh token（含内部 commit）
    await TokenService(session).revoke_all_user_refresh(str(user.id))

    logger.info(f"管理端软禁用用户: {user.username} (操作者: {current_user.username or current_user.id})")
    return {
        "code": 200,
        "message": "已禁用",
        "data": None,
        "timestamp": int(datetime.now().timestamp() * 1000),
    }


@router.put("/{user_id}/reset-password", response_model=dict)
async def reset_user_password(
    user_id: str,
    current_user: UserModel = require_permission("manage:user:reset_password"),
    session: AsyncSession = Depends(get_session),
) -> dict:
    """
    重置用户密码（生成 12 位随机临时密码）

    需要 manage:user:reset_password 权限；
    写 hash + must_change_password=True + token_version+1 + 吊销全部 refresh。
    明文临时密码只在响应体返回一次（tempPassword），不写日志、不落盘。
    """
    user = await _get_user_or_404(session, user_id)

    temp_password = generate_temp_password()
    user.password_hash = _pwd_context.hash(temp_password)
    user.must_change_password = True
    user.token_version = (user.token_version or 0) + 1
    await session.commit()
    await TokenService(session).revoke_all_user_refresh(str(user.id))

    # 此处不记录临时密码，只记录动作
    logger.info(f"管理端重置密码: {user.username} (操作者: {current_user.username or current_user.id})")
    return {
        "code": 200,
        "message": "密码已重置",
        "data": {"tempPassword": temp_password},
        "timestamp": int(datetime.now().timestamp() * 1000),
    }
