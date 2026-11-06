"""OAuth 自动接入（Install Flow）端点

协议契约（权威）：``docs/superpowers/contracts/2026-11-06-e101-oauth2-install-contract.md``

端点分两类：

**未认证发起 / 服务端到服务端**（小蓝后端调用；滥用上限见服务层）：
- ``POST /api/oauth2/install/requests``      —— 发起安装申请（未认证；配额与速率受限）
- ``POST /api/oauth2/install/status``         —— 查询状态（verifier 鉴权，走 body 不进 URL）
- ``POST /api/oauth2/install/exchange``       —— 兑换密钥（verifier 鉴权；单次消费 + 恢复窗口）

**管理员 SPA**（需 ``role == "admin"``）：
- ``GET  /api/oauth2/install/requests``              —— 审计列表（最近 50 条，不含敏感字段）
- ``GET  /api/oauth2/install/requests/{install_id}`` —— 确认页详情
- ``POST /api/oauth2/install/requests/{install_id}/approve`` —— 批准（签发一次性安装码）
- ``POST /api/oauth2/install/requests/{install_id}/reject``  —— 拒绝

安全口径：
- **无长期凭据**：OpenTask 只存 ``challenge = S256(verifier)``；
- **密钥零落库明文**：``client_secret`` 只在兑换响应体出现一次（client 在兑换时才创建）；
- **consumed ≠ 成功**：只有 2xx 且响应体含 ``client_secret`` 才算成功；
- **日志零泄漏**：本模块不打印 code / verifier / challenge / client_secret / state。
"""

import logging
from datetime import datetime, timedelta
from typing import Optional
from urllib.parse import urlsplit

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from opentask.auth import authenticate
from opentask.config import config
from opentask.models.user.model import UserModel
from opentask.repositories.base import get_session
from opentask.services.oauth2.install_service import (
    InstallAuthError,
    InstallConflictError,
    InstallLimitError,
    InstallNotFoundError,
    InstallValidationError,
    OAuthInstallService,
)
from opentask.utils.response import success_response

from .schemas import (
    InstallDecisionView,
    InstallExchangeRequest,
    InstallExchangeView,
    InstallRequestCreate,
    InstallRequestCreated,
    InstallRequestView,
    InstallStatusRequest,
    InstallStatusView,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["OAuth2-Install"])


# ===== 工具 =====


def _require_admin(current_user: UserModel) -> None:
    """管理端点：仅 admin 角色（与既有 /api/oauth2/clients 口径一致）"""
    if current_user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="需要管理员权限")


def _http_error(code: str, message: str, http_status: int) -> HTTPException:
    """统一错误形状：{error, error_description}（与既有 OAuth2 错误风格一致）"""
    return HTTPException(
        status_code=http_status,
        detail={"error": code, "error_description": message},
    )


def _client_ip(request: Request) -> Optional[str]:
    """请求来源 IP（限流与管理员可信度判断用）"""
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()[:64]
    if request.client:
        return request.client.host[:64]
    return None


def _approval_url(request: Request, install_id: str) -> tuple[str, str]:
    """管理员确认页地址 → (绝对地址, 相对路径)

    绝对地址优先用 ``config.frontend_base_url``；未配置时回退到请求自身 origin；
    两者都没有时只给相对路径（由接入方按自己的前端 origin 拼接）。
    """
    path = f"/oauth2/install/{install_id}"
    base = (config.frontend_base_url or "").rstrip("/")
    if not base:
        forwarded_host = request.headers.get("x-forwarded-host") or request.headers.get("host")
        forwarded_proto = request.headers.get("x-forwarded-proto") or request.url.scheme
        if forwarded_host:
            base = f"{forwarded_proto}://{forwarded_host}"
    return (f"{base}{path}" if base else path), path


def _request_view(record) -> InstallRequestView:
    """申请 → 视图（**不含** 安装码 / challenge / state）"""
    return InstallRequestView(
        install_id=str(record.id),
        status=record.status,
        client_id=record.client_id,
        name=record.name,
        description=record.description,
        redirect_uris=[uri for uri in record.redirect_uris.split(",") if uri],
        scopes=sorted(record.scopes.split()) if record.scopes else [],
        grant_types=sorted(record.grant_types.split()) if record.grant_types else [],
        callback_url=record.callback_url,
        callback_host=(urlsplit(record.callback_url).hostname or ""),
        expires_at=record.expires_at.isoformat() if record.expires_at else "",
        created_at=record.created_at.isoformat() if record.created_at else "",
        approved_at=record.approved_at.isoformat() if record.approved_at else None,
        consumed_at=record.consumed_at.isoformat() if record.consumed_at else None,
        recovery_count=record.recovery_count or 0,
        request_ip=record.request_ip,
        user_agent=record.user_agent,
    )


# ===== 未认证发起 / 服务端到服务端 =====


@router.post(
    "/api/oauth2/install/requests",
    summary="发起 OAuth 安装申请（未认证；受配额与速率限制）",
)
async def create_install_request(
    body: InstallRequestCreate,
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    """小蓝后端发起安装申请

    - 幂等：同 ``client_id`` + 同 ``code_challenge`` → 复用既有申请（``reused: true``）；
    - 配额：全局 pending 上限、单 IP pending 上限、单 IP 每分钟速率上限；
    - 校验：PKCE 只接受 S256、回调地址绝对 URL、callback 主机须绑定 redirect 主机。
    """
    service = OAuthInstallService(session)
    try:
        record, reused = await service.create_request(
            client_id=body.client_id,
            name=body.name,
            description=body.description,
            redirect_uris=body.redirect_uris,
            scopes=body.scopes,
            grant_types=body.grant_types,
            callback_url=body.callback_url,
            state=body.state,
            code_challenge=body.code_challenge,
            code_challenge_method=body.code_challenge_method,
            request_ip=_client_ip(request),
            user_agent=request.headers.get("user-agent"),
        )
    except InstallValidationError as exc:
        raise _http_error("invalid_request", str(exc), status.HTTP_422_UNPROCESSABLE_ENTITY)
    except InstallConflictError as exc:
        raise _http_error(exc.code, str(exc), status.HTTP_409_CONFLICT)
    except InstallLimitError as exc:
        raise _http_error(exc.code, str(exc), status.HTTP_429_TOO_MANY_REQUESTS)

    approval_url, approval_path = _approval_url(request, str(record.id))
    return success_response(
        data=InstallRequestCreated(
            install_id=str(record.id),
            status=record.status,
            approval_url=approval_url,
            approval_path=approval_path,
            expires_at=record.expires_at.isoformat() if record.expires_at else "",
            reused=reused,
        )
    )


@router.post(
    "/api/oauth2/install/status",
    summary="查询安装申请状态（verifier 鉴权）",
)
async def install_status(
    body: InstallStatusRequest,
    session: AsyncSession = Depends(get_session),
):
    """查询申请状态——**不含任何密钥**

    verifier 不匹配时返回 404（不泄露申请是否存在）。
    """
    service = OAuthInstallService(session)
    record = await service.get_request(body.install_id)
    if record is None or not service.verifier_matches(record, body.verifier):
        raise _http_error(
            "install_request_not_found", "安装申请不存在", status.HTTP_404_NOT_FOUND
        )

    now = datetime.utcnow()
    recoverable = bool(
        record.status == "CONSUMED"
        and (record.first_exchange_at or record.consumed_at)
        and now
        <= (record.first_exchange_at or record.consumed_at)
        + timedelta(seconds=config.oauth_install_recovery_window_seconds)
    )
    return success_response(
        data=InstallStatusView(
            install_id=str(record.id),
            status=record.status,
            client_id=record.client_id,
            created_at=record.created_at.isoformat() if record.created_at else "",
            expires_at=record.expires_at.isoformat() if record.expires_at else "",
            approved_at=record.approved_at.isoformat() if record.approved_at else None,
            consumed_at=record.consumed_at.isoformat() if record.consumed_at else None,
            recoverable=recoverable,
        )
    )


@router.post(
    "/api/oauth2/install/exchange",
    summary="兑换 client 密钥（verifier 鉴权；单次消费 + 恢复窗口）",
)
async def exchange_install(
    body: InstallExchangeRequest,
    session: AsyncSession = Depends(get_session),
):
    """服务端兑换：安装码 + verifier → client_id + client_secret

    - **只有 2xx 且响应体含 ``client_secret`` 才算成功**；
    - 已消费且在恢复窗口内 → 轮换换发**新密钥**（``recovered: true``）；
    - 窗口外 → 409 ``install_already_consumed``（**失败**，须重新发起安装）。
    """
    service = OAuthInstallService(session)
    try:
        credentials = await service.exchange(
            body.install_id, body.code, body.verifier
        )
    except InstallAuthError as exc:
        raise _http_error(exc.code, str(exc), status.HTTP_400_BAD_REQUEST)
    except InstallConflictError as exc:
        raise _http_error(exc.code, str(exc), status.HTTP_409_CONFLICT)
    except InstallNotFoundError as exc:
        raise _http_error(exc.code, str(exc), status.HTTP_404_NOT_FOUND)
    except InstallValidationError as exc:
        raise _http_error("invalid_request", str(exc), status.HTTP_422_UNPROCESSABLE_ENTITY)

    return success_response(data=InstallExchangeView(**credentials))


# ===== 管理员端点 =====


@router.get(
    "/api/oauth2/install/requests",
    summary="安装申请审计列表（管理员）",
)
async def list_install_requests(
    limit: int = 50,
    current_user: UserModel = Depends(authenticate),
    session: AsyncSession = Depends(get_session),
):
    """列出最近安装申请（**不含** 安装码 / challenge / state）"""
    _require_admin(current_user)
    records = await OAuthInstallService(session).list_requests(limit=min(limit, 50))
    return success_response(data=[_request_view(record) for record in records])


@router.get(
    "/api/oauth2/install/requests/{install_id}",
    summary="安装申请详情（管理员确认页用）",
)
async def get_install_request(
    install_id: str,
    current_user: UserModel = Depends(authenticate),
    session: AsyncSession = Depends(get_session),
):
    """确认页展示用详情（含来源 IP / UA 与 callback 主机，便于核对可信度）"""
    _require_admin(current_user)
    service = OAuthInstallService(session)
    try:
        record = await service.get_by_id_or_404(install_id)
    except InstallNotFoundError as exc:
        raise _http_error(exc.code, str(exc), status.HTTP_404_NOT_FOUND)
    return success_response(data=_request_view(record))


@router.post(
    "/api/oauth2/install/requests/{install_id}/approve",
    summary="批准安装（管理员）",
)
async def approve_install_request(
    install_id: str,
    current_user: UserModel = Depends(authenticate),
    session: AsyncSession = Depends(get_session),
):
    """批准安装 → 签发**一次性安装码**并回跳到申请方 callback_url

    - 幂等保护：仅 ``PENDING`` 可批准，重复批准 → 409；
    - 批准阶段**不创建 client**（client 在兑换时才创建，密钥零落库明文）；
    - 回跳响应头：``no-referrer`` / ``no-store`` / ``nosniff``。
    """
    _require_admin(current_user)
    service = OAuthInstallService(session)
    try:
        record, _code, redirect_to = await service.approve(install_id, str(current_user.id))
    except InstallNotFoundError as exc:
        raise _http_error(exc.code, str(exc), status.HTTP_404_NOT_FOUND)
    except InstallConflictError as exc:
        raise _http_error(exc.code, str(exc), status.HTTP_409_CONFLICT)
    except InstallValidationError as exc:
        raise _http_error("invalid_request", str(exc), status.HTTP_422_UNPROCESSABLE_ENTITY)

    return success_response(
        data=InstallDecisionView(
            install_id=str(record.id), status=record.status, redirect_to=redirect_to
        )
    )


@router.post(
    "/api/oauth2/install/requests/{install_id}/reject",
    summary="拒绝安装（管理员）",
)
async def reject_install_request(
    install_id: str,
    current_user: UserModel = Depends(authenticate),
    session: AsyncSession = Depends(get_session),
):
    """拒绝安装申请"""
    _require_admin(current_user)
    service = OAuthInstallService(session)
    try:
        record = await service.reject(install_id, str(current_user.id))
    except InstallNotFoundError as exc:
        raise _http_error(exc.code, str(exc), status.HTTP_404_NOT_FOUND)
    except InstallConflictError as exc:
        raise _http_error(exc.code, str(exc), status.HTTP_409_CONFLICT)
    return success_response(
        data=InstallDecisionView(install_id=str(record.id), status=record.status)
    )
