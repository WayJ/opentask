import logging
import httpx
from datetime import datetime, timedelta, timezone
from typing import Optional
from typing_extensions import Annotated
from pydantic import BaseModel, Field

from fastapi import APIRouter, Body, Depends, Response, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession

from opentask.auth import authenticate
from opentask.repositories.base import get_session
from opentask.repositories.user import UserRepository
from opentask.services.user_center.auth_service import AuthService
from opentask.services.user_center.dingtalk.client import DingTalkClient, DingTalkError
from opentask.services.user_center.dingtalk.oauth_service import DingTalkOAuthService
from opentask.services.user_center.token_service import TokenService

from opentask.utils.response import success_response as std_success_response, StatusCode
from opentask.config import config
from opentask.utils.encrypt import encrypt_password
from opentask.utils.token_security import encrypt_jnpf_token

logger = logging.getLogger(__name__)


router = APIRouter(
    prefix="/api/auth",
    tags=["auth"],
    responses={401: {"description": "Incorrect username or password"}},
)


def success_response(data: dict = None, message: str = "success"):
    """统一成功响应格式（兼容旧接口，使用新的标准格式）"""
    return std_success_response(data=data, message=message, code=StatusCode.SUCCESS)


class RefreshTokenBody(BaseModel):
    """refresh token 请求体（logout 时可不带 body）"""
    refreshToken: Optional[str] = None


class ChangePasswordBody(BaseModel):
    """修改密码请求体"""
    oldPassword: str
    newPassword: str


class DingTalkCallbackBody(BaseModel):
    """钉钉免登回调请求体（前端拿到 authCode 后调用）"""
    authCode: str


def _build_dingtalk_client() -> DingTalkClient:
    """按配置构造钉钉客户端；未配置凭据 → 400（免登禁止空凭据调用）

    独立成模块级函数便于测试注入 FakeDingTalkClient。
    """
    if not (config.dingtalk_app_key and config.dingtalk_app_secret):
        raise HTTPException(status_code=400, detail="未配置钉钉应用凭据")
    try:
        return DingTalkClient(config.dingtalk_app_key, config.dingtalk_app_secret)
    except DingTalkError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.post("/login")
async def login(
    username: Annotated[str, Body(alias="userName", alias_priority=2)],
    password: Annotated[str, Body()],
    request: Request,
    session=Depends(get_session),
):
    """
    用户登录：JNPF 启用时走 JNPF 认证，否则走本地账号认证（spec 3.2）

    本地路径：
    - AuthService.login_local 校验密码/锁定/禁用状态并签发 token 对

    JNPF 路径：
    1. 登录前先查本地同步用户，禁用（status!=1）直接 403
    2. 转发登录请求到 JNPF 平台验证
    3. 验证成功后从 JNPF 获取用户信息
    4. 同步用户信息到 opentask 数据库（加密存储 JNPF token）
    5. TokenService.issue_tokens 签发 access + refresh token 对
    6. 记录安全审计日志

    安全改进：
    - access JWT 不落库，每次登录重新签发
    - JNPF token 加密存储
    - 使用时区感知的 datetime
    """
    client_ip = request.client.host if request.client else "unknown"
    user_agent = request.headers.get("user-agent")
    logger.info(f"登录请求 - 用户名: {username}, IP: {client_ip}")

    # 未启用 JNPF：走本地账号登录
    if not config.jnpf_enabled:
        auth = AuthService(session)
        user, pair = await auth.login_local(
            username, password, user_agent=user_agent, ip=client_ip
        )
        return success_response({
            **pair,
            "username": user.username or user.name or username,
            "userId": str(user.id),
            "jnpfName": user.jnpf_name,
            "name": user.name,
        })

    # 0. 登录前查本地同步用户：已禁用的账号不允许再走 JNPF 登录
    from opentask.repositories.base import NotFoundError
    try:
        existing_user = await UserRepository().get_by_name(session, username)
    except NotFoundError:
        existing_user = None
    if existing_user is not None and existing_user.status != 1:
        logger.warning(f"JNPF 登录拒绝禁用用户: {username}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="用户已被禁用",
        )

    # 1. 调用 JNPF 登录接口验证用户凭据
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            # 调用 JNPF 登录接口
            jnpf_response = await client.post(
                f"{config.jnpf_base_url}/api/oauth/Login",
                headers={
                    "Content-Type": "application/x-www-form-urlencoded",
                    "App-Code": config.jnpf_app_code,
                    "Jnpf-Origin": "pc",
                    "Vue-Version": "3"
                },
                data={
                    "account": username,
                    # 前端已改为明文提交，JNPF 平台要求密文（MD5+AES-ECB+Hex），
                    # 加密责任收归后端（与前端旧 encrypt.ts 等价，见 utils/encrypt.py）。
                    # 兼容性：本分支只服务新前端（同版本发布），不再接受旧前端的密文提交——
                    # 明文/密文均为任意字符串，服务端无法可靠区分。
                    "password": encrypt_password(password),
                    "code": "",
                    "origin": "password",
                    "timestamp": "0",
                    "jnpf_ticket": "",
                    "grant_type": "password"
                }
            )

            if jnpf_response.status_code != 200:
                logger.error(f"JNPF 登录失败: {jnpf_response.status_code}")
                # 尝试读取响应体获取详细错误信息
                try:
                    error_data = jnpf_response.json()
                    error_msg = error_data.get("msg", "用户名或密码错误")
                    logger.error(f"JNPF 响应详情: {error_data}")
                except:
                    error_msg = "用户名或密码错误"
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail=error_msg
                )

            jnpf_data = jnpf_response.json()

            # 检查 JNPF 响应
            if jnpf_data.get("code") != 200:
                error_msg = jnpf_data.get("msg", "用户名或密码错误")
                logger.error(f"JNPF 登录失败: {error_msg}")
                logger.error(f"JNPF 响应详情: {jnpf_data}")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail=error_msg
                )

            # 获取 JNPF token
            jnpf_token = jnpf_data.get("data", {}).get("token")
            logger.debug("JNPF login response received")

            # 🔒 加密 JNPF token 后存储
            encrypted_jnpf_token = encrypt_jnpf_token(jnpf_token)
            logger.debug(f"JNPF token 已加密存储")

            # JNPF token 已包含 "bearer " 前缀，根据文档直接使用完整 token
            # 2. 使用 JNPF token 获取用户信息
            user_info_response = await client.get(
                f"{config.jnpf_base_url}/api/oauth/CurrentUser",
                headers={
                    "Authorization": jnpf_token,  # 直接使用完整 token（包含 bearer 前缀）
                    "App-Code": config.jnpf_app_code,
                    "Jnpf-Origin": "pc",
                    "Vue-Version": "3"
                },
                # params={
                #     "systemCode": "ACCS",
                #     "isBackend": "0"
                # }
            )

            logger.debug(f"JNPF CurrentUser 响应状态: {user_info_response.status_code}")

            if user_info_response.status_code != 200:
                logger.error(f"获取 JNPF 用户信息失败: {user_info_response.status_code}")
                # 尝试读取响应体获取详细错误信息
                try:
                    error_data = user_info_response.json()
                    error_msg = error_data.get("msg", "获取用户信息失败")
                    logger.error(f"JNPF 响应详情: {error_data}")
                except:
                    error_msg = "获取用户信息失败"
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail=error_msg
                )

            user_info_data = user_info_response.json()

            if user_info_data.get("code") != 200:
                error_msg = user_info_data.get("msg", "获取用户信息失败")
                logger.error(f"获取 JNPF 用户信息失败: {error_msg}")
                logger.error(f"JNPF 响应详情: {user_info_data}")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail=error_msg
                )

            # 提取用户详细信息
            jnpf_user_data = user_info_data.get("data", {})
            jnpf_user_info = jnpf_user_data.get("userInfo", {})

            logger.info(f"获取到 JNPF 用户信息: {jnpf_user_info.get('userName')}")

            # 3. 同步用户信息到 opentask 数据库（existing_user 已在步骤 0 查过）
            user = existing_user

            # 4. 每次登录重新签发 token
            # （原指纹复用逻辑只写不验，已剥离；每次登录重新签发，语义不变）
            # 注意：user 表的时间列为 timestamp without time zone（模型 DateTime 无 tz），
            # asyncpg 严禁把带 tz 的 datetime 绑定到 naive 列，必须用 naive UTC
            now = datetime.utcnow()
            expires_at = now + timedelta(days=7)

            if user is None:
                # 创建新用户
                from opentask.models.user.model import UserModel
                user = UserModel(
                    name=username,
                    jnpf_user_id=jnpf_user_info.get("userId", ""),
                    jnpf_account=jnpf_user_info.get("userAccount", ""),
                    jnpf_name=jnpf_user_info.get("userName", username),
                    jnpf_token=encrypted_jnpf_token,  # 🔒 加密存储
                    jwt_expires_at=expires_at,
                    last_login_time=now
                )
                session.add(user)
                logger.info(f"创建新用户: {username}")
            else:
                # 更新现有用户 - 使用UPDATE语句避免session问题
                from opentask.models.user.model import UserModel
                from sqlalchemy import update
                await session.execute(
                    update(UserModel.__table__)
                    .where(UserModel.id == user.id)
                    .values(
                        jnpf_token=encrypted_jnpf_token,
                        jwt_expires_at=expires_at,
                        last_login_time=now
                    )
                )
                logger.info(f"更新用户 {username}（重新签发 token）")

            await session.commit()

            # 签发 access + refresh token 对（sub=str(user.id) / tv=token_version）
            pair = await TokenService(session).issue_tokens(
                user, user_agent=user_agent, ip=client_ip
            )

            # 安全审计日志
            logger.info(
                f"JWT_ISSUED user={username} "
                f"expires_at={expires_at.isoformat()} ip={client_ip}"
            )

            # 5. 返回 token 和用户信息
            return success_response({
                **pair,
                "username": jnpf_user_info.get("userName", username),  # 使用 JNPF 的 userName 作为 username
                "userId": str(user.id),
                "userAccount": jnpf_user_info.get("userAccount", ""),
                "organizeId": jnpf_user_info.get("organizeId", ""),
                "organizeName": jnpf_user_info.get("organizeName", "")
            })

    except httpx.TimeoutException:
        logger.error("JNPF API 请求超时")
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="请求超时"
        )
    except httpx.RequestError as e:
        logger.error(f"JNPF API 请求失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="服务暂时不可用"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"登录失败: {type(e).__name__}: {e}")
        import traceback
        logger.error(f"堆栈:\n{traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="登录失败"
        )


@router.post("/refresh-token")
@router.post("/refreshToken")  # 旧路径别名（前端 shared.ts 调用）
async def refresh_token(
    body: RefreshTokenBody,
    request: Request,
    session=Depends(get_session),
):
    """
    刷新 token：用 refresh token 换新的 token 对（轮换式，旧 refresh 立即吊销）

    检测到已吊销 token 重放时，服务端会吊销该用户全部会话（疑似泄漏强制下线）。
    """
    if not body.refreshToken:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="refreshToken 不能为空",
        )

    client_ip = request.client.host if request.client else "unknown"
    user_agent = request.headers.get("user-agent")

    pair = await TokenService(session).rotate_refresh(
        body.refreshToken, user_agent=user_agent, ip=client_ip
    )
    return success_response(pair)


@router.post("/logout")
async def logout(
    body: Optional[RefreshTokenBody] = Body(default=None),
    session=Depends(get_session),
):
    """
    用户登出

    带 refreshToken 时服务端吊销该 refresh；无 body 时也返回成功
    （access JWT 短时效 + 客户端自清即可）。
    """
    if body and body.refreshToken:
        await TokenService(session).revoke_refresh(body.refreshToken)
    return std_success_response(message="Successfully logged out")


@router.post("/change-password")
async def change_password(
    body: ChangePasswordBody,
    request: Request,
    current_user=Depends(authenticate),
    session=Depends(get_session),
):
    """
    修改密码（依赖 authenticate；pwd_change scope 的受限 token 只放行本端点）

    成功后：token_version+1（旧 access 全失效）、吊销全部旧 refresh、
    返回新的正常 token 对，前端直接替换本地存储。
    """
    client_ip = request.client.host if request.client else "unknown"
    user_agent = request.headers.get("user-agent")

    auth = AuthService(session)
    pair = await auth.change_password(
        current_user,
        body.oldPassword,
        body.newPassword,
        user_agent=user_agent,
        ip=client_ip,
    )
    return success_response(pair)


@router.post("/login-local")
async def login_local(
    username: Annotated[str, Body(alias="userName", alias_priority=2)],
    password: Annotated[str, Body()],
    request: Request,
    session=Depends(get_session),
):
    """
    opentask 本地账号登录（保留兼容旧客户端，内部与 /login 未启用 JNPF 时的路径一致）

    与 /login(JNPF) 的区别：
    - /login: 走 JNPF 单点登录，需要加密密码
    - /login-local: 使用 opentask 自有账号，密码不加密，直接验证

    Args:
        username: 用户名
        password: 明文密码（不加密）

    Returns:
        token 对（access + refresh）和用户信息
    """
    logger.info(f"本地登录请求 - 用户名: {username}")

    client_ip = request.client.host if request.client else "unknown"
    user_agent = request.headers.get("user-agent")

    auth = AuthService(session)
    user, pair = await auth.login_local(
        username, password, user_agent=user_agent, ip=client_ip
    )

    logger.info(f"本地登录成功 - 用户: {username}, ID: {user.id}")

    # 返回 token 和用户信息
    return success_response({
        **pair,
        "username": user.username or user.name or username,
        "userId": str(user.id),
        "jnpfName": user.jnpf_name,
        "name": user.name,
    })


@router.get("/dingtalk/config")
async def dingtalk_config():
    """
    钉钉登录配置（免鉴权）：前端登录页据此决定是否展示钉钉登录入口。

    enabled = AppKey 与 AppSecret 均已配置；未配置时 appKey 返回 None
    （只下发 AppKey，AppSecret 永不出后端）。
    """
    enabled = bool(config.dingtalk_app_key and config.dingtalk_app_secret)
    return success_response({
        "enabled": enabled,
        "appKey": config.dingtalk_app_key if enabled else None,
    })


@router.post("/dingtalk/callback")
async def dingtalk_callback(
    body: DingTalkCallbackBody,
    request: Request,
    session=Depends(get_session),
):
    """
    钉钉免密登录（Phase 4 Task 3）：前端扫码/内网免登拿到 authCode 后回调

    authCode → userid → 用户详情 → 本地用户定位/自动建号 → 签发 token 对。
    - 已绑定用户：禁用 403；正常直接签发
    - 新用户：dingtalk_auto_register=true 自动建号（role=viewer）；关闭 403
    - 凭据未配置 → 400；钉钉 API 失败（DingTalkError）→ 502
    """
    client_ip = request.client.host if request.client else "unknown"
    user_agent = request.headers.get("user-agent")

    client = _build_dingtalk_client()
    try:
        user, pair = await DingTalkOAuthService(session, client).login_by_code(
            body.authCode, user_agent=user_agent, ip=client_ip
        )
    except HTTPException:
        raise
    except DingTalkError as e:
        logger.error(f"钉钉免登失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"钉钉免登失败: {e}",
        ) from e

    return success_response({
        **pair,
        "username": user.username or user.name or "",
        "userId": str(user.id),
        "jnpfName": user.jnpf_name,
        "name": user.name,
    })


@router.get("/getUserInfo")
async def get_user_info(
    current_user=Depends(authenticate),
    session: AsyncSession = Depends(get_session),
):
    """
    获取当前用户信息：真实角色 + 权限下发（Phase 3 Task 3）

    - roles：RbacService 解析的角色编码（user_role 关联表优先，桥接 user.role）；
      未播种库（role 表空）时桥接失败，直接下发 user.role 字符串兜底
      （角色码不依赖播种，避免生产库漏播种时前端拿不到角色）
    - buttons：button 类权限码（manage:user:create 等，前端 v-per指令用）
    - menus：menu 类权限码对应的 route_key 列表（前端动态菜单/路由用）
    - userName：jnpf_name 优先（前端 user-avatar/欢迎语依赖该字段）
    """
    from sqlalchemy import select

    from opentask.models.user_center import Permission
    from opentask.services.user_center.rbac_service import RbacService

    rbac = RbacService(session)
    roles = await rbac.get_user_role_codes(current_user)
    if not roles:
        # 未播种库兜底：角色码本身不依赖播种，桥接字符串直接下发
        legacy_role = getattr(current_user, "role", None)
        if legacy_role:
            roles = [legacy_role]

    permissions = await rbac.get_user_permissions(current_user)
    buttons: list[str] = []
    menus: list[str] = []
    if permissions:
        # 一次查询全量权限行，按 type 拆分 buttons / menus
        result = await session.execute(
            select(Permission).where(Permission.code.in_(permissions))
        )
        for perm in result.scalars().all():
            if perm.type == "menu":
                if perm.route_key:
                    menus.append(perm.route_key)
            else:
                buttons.append(perm.code)

    return success_response({
        "userId": str(current_user.id),
        "userName": current_user.jnpf_name or current_user.name or current_user.username,
        "roles": roles,
        "buttons": buttons,
        "menus": menus,
    })


@router.head("/login")
async def login_head() -> Response:
    return Response(status_code=200)
