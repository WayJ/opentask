import logging
from typing import Optional
from uuid import UUID

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from starlette.status import HTTP_401_UNAUTHORIZED

from opentask.jwt_utils import verify_token
from opentask.repositories.base import get_session, AsyncSession, NotFoundError
from opentask.repositories.user import UserRepository
from opentask.models.user.model import UserModel

logger = logging.getLogger(__name__)

# 使用HTTPBearer来获取Authorization header中的token
# auto_error=False：缺少/格式错误的 Authorization 头由下方显式抛 401，
# 而不是 FastAPI HTTPBearer 默认的 403（401=未认证，403=已认证但无权限）
security = HTTPBearer(auto_error=False)


def _is_uuid(value: str) -> bool:
    """判断字符串是否为 UUID 格式（新 token sub=str(user.id)，旧 token sub=用户名）"""
    try:
        UUID(value)
        return True
    except (ValueError, AttributeError, TypeError):
        return False


async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    session: AsyncSession = Depends(get_session)
) -> Optional[UserModel]:
    """从JWT token或Access Token中获取当前用户信息

    认证优先级：
    1. 先尝试 JWT Token 验证
    2. JWT 失败后，尝试 Access Token 验证（以 vk_ 开头）

    JWT 校验链：
    - 用户查找双路径：sub 是 UUID → 按 id 查；否则按 username 查（回退 name，兼容存量 token）
    - tv claim（缺失视为 0）≠ user.token_version → 401（改密/批量吊销后旧 token 失效）
    - scp=pwd_change 的受限 token 只能访问改密端点，其余路径 403
    - status != 1 的禁用用户立即失效
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    # HTTPBearer(auto_error=False) 时无凭据返回 None：显式按 401 处理
    if credentials is None:
        raise credentials_exception

    token_value = credentials.credentials

    # 如果 token 以 vk_ 开头，直接走 Access Token 验证
    if token_value.startswith("vk_"):
        try:
            from opentask.services.access_token.service import AccessTokenService
            service = AccessTokenService(session)
            user = await service.validate_token(token_value)
            if user:
                logger.debug(f"Access Token auth success: user={user.name}")
                return user
            raise credentials_exception
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Access Token validation error: {e}")
            raise credentials_exception

    # JWT Token 验证（原有逻辑）
    try:
        payload = verify_token(token_value)
        sub: str = payload.get("sub")
        if sub is None:
            raise credentials_exception
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Token validation error: {e}")
        raise credentials_exception

    # 用户查找双路径：新 token sub=用户 id（UUID），旧 token sub=用户名
    user_repo = UserRepository()
    user = None
    try:
        if _is_uuid(sub):
            try:
                user = await user_repo.get_by_uuid(session, UUID(sub))
            except NotFoundError:
                # UUID 形态的用户名（极少见）：按 id 查不到时回退按用户名查
                user = None
        if user is None:
            # 先按 username 列查，查不到回退 name 列（兼容存量 token 的 sub=name）
            user = await user_repo.get_by_username(session, sub)
        if user is None:
            user = await user_repo.get_by_name(session, sub)
    except NotFoundError:
        user = None
    except Exception as e:
        logger.error(f"User not found: {e}")
        raise credentials_exception

    if user is None:
        raise credentials_exception

    # token 版本校验：tv 缺失视为 0；改密后 token_version+1，旧 access 全部失效
    token_version = payload.get("tv", 0)
    if token_version != (user.token_version or 0):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="登录态已失效，请重新登录",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 受限 token（scp=pwd_change）只放行改密端点
    if payload.get("scp") == "pwd_change" and request.url.path != "/api/auth/change-password":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="请先修改初始密码",
        )

    # 禁用用户（status != 1）立即失效，即使 JWT 本身未过期
    if user.status != 1:
        logger.warning(f"Disabled user attempted access: {sub}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户已被禁用",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


async def validate_credentials_db(username: str, password: str, session: AsyncSession) -> bool:
    """[DEPRECATED] 在数据库中验证用户凭据

    已由 AuthService.login_local 取代，保留此函数仅为兼容旧调用方；
    注意：不再有配置文件密码兜底，无 password_hash 的用户一律 401。
    """
    from opentask.services.user_center.auth_service import AuthService

    auth = AuthService(session)
    await auth.login_local(username, password)
    return True


async def authenticate(request: Request, current_user: UserModel = Depends(get_current_user)) -> UserModel:
    """认证依赖函数，返回当前用户信息（UserModel对象）"""
    # 将用户对象存储到 request.state，供其他依赖使用
    request.state.user = current_user
    return current_user


async def authenticate_dict(current_user: UserModel = Depends(get_current_user)) -> dict:
    """认证依赖函数，返回当前用户信息（字典格式，用于auth接口）"""
    return {
        "id": str(current_user.id),
        "name": current_user.name,
        "role": current_user.role,
        "jnpf_user_id": current_user.jnpf_user_id,
        "jnpf_account": current_user.jnpf_account,
        "jnpf_name": current_user.jnpf_name,
        "organize_name": current_user.organize_name,
        "position_name": current_user.position_name,
        "status": current_user.status,
    }


# 保留旧的Basic Auth方式作为备用（如果需要）
def validate_credentials(username: str, password: str) -> bool:
    """旧的配置文件验证方式，保留作为备用"""
    import secrets
    from opentask.config import config

    correct_username = secrets.compare_digest(username, str(config.auth_username))
    correct_password = secrets.compare_digest(password, str(config.auth_password))
    if not (correct_username and correct_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )
    return True