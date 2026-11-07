"""OAuth2 Provider API 路由

端点分两类：

**标准 OAuth2 协议端点**（消费者服务端直连，不经 SPA）：
- ``POST /oauth2/token``     —— RFC 6749 §3.2 授权码 / refresh 换令牌
- ``GET  /oauth2/userinfo``   —— 用户信息（绑定对齐用）
- ``POST /oauth2/revoke``     —— RFC 7009 吊销

**SPA 支撑端点**（浏览器授权入口的配套，**需 OpenTask 会话**）：
- ``GET  /api/oauth2/authorize/context`` —— 校验授权请求并返回同意页上下文
- ``POST /api/oauth2/authorize/approve`` —— 同意/拒绝 → 返回应跳转 URL

**管理端点**（需 admin 角色）：
- ``GET/POST/PATCH/DELETE /api/oauth2/clients``、``POST /api/oauth2/clients/{id}/rotate-secret``

浏览器授权入口本身是 **前端 SPA 路由** ``/oauth2/authorize``（前后端分离部署，
浏览器导航不带 Authorization 头，认证必须由 SPA 走会话完成）。客户端把
SPA 地址登记为 authorization_endpoint；标准令牌端点仍是 ``/oauth2/token``。
"""

import logging
import re
import secrets
from datetime import datetime, timedelta
from urllib.parse import urlsplit
from typing import Optional
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, Form, HTTPException, Query, status
from fastapi.responses import JSONResponse
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from opentask.auth import authenticate
from opentask.config import config
from opentask.models.oauth2.model import OAuthClient
from opentask.models.user.model import UserModel
from opentask.services.oauth2.authorization_service import (
    AuthorizationCodeService,
    InvalidGrantError,
)
from opentask.services.oauth2.client_service import (
    ClientNotFoundError,
    ClientSecretError,
    GrantTypeError,
    OAuthClientService,
    RedirectUriError,
    ScopeError,
    split_redirect_uris,
    split_scopes,
)
from opentask.services.oauth2.token_service import (
    InvalidTokenError,
    OAuthTokenService,
    ReplayDetectedError,
    TokenRevokedError,
)
from opentask.utils.response import success_response

from .dependencies import get_oauth_session, require_oauth_scope
from .metadata import public_origin
from .schemas import (
    AuthorizeContextRequest,
    AuthorizeContextView,
    AuthorizeDecisionRequest,
    AuthorizeDecisionResponse,
    OAuthClientCreate,
    OAuthClientCreated,
    OAuthClientUpdate,
    OAuthClientView,
    OAuthErrorResponse,
    OAuthRevokeRequest,
    OAuthTokenResponse,
    OAuthUserInfo,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["OAuth2"])


# ===== 工具 =====

# 动态客户端只负责登记；用户仍须逐人授权。配额使用事务级 PostgreSQL 锁，
# 防止并发注册绕过上限；配额由管理员清理不再使用的客户端后释放。
_DCR_MAX_CLIENTS = 1000
_DCR_PER_MINUTE = 10
_MCP_SCOPES = {"profile", "read:tasks", "read:projects", "read:requirements", "read:members", "write:tasks"}


@router.get("/.well-known/oauth-protected-resource/mcp")
@router.get("/.well-known/oauth-protected-resource")
async def mcp_resource_metadata():
    origin = public_origin()
    return {"resource": origin + "/mcp", "authorization_servers": [origin],
            "scopes_supported": sorted(_MCP_SCOPES), "bearer_methods_supported": ["header"]}


@router.get("/.well-known/oauth-authorization-server")
async def oauth_server_metadata():
    origin = public_origin()
    return {"issuer": origin, "authorization_endpoint": origin + "/oauth2/authorize",
            "token_endpoint": origin + "/oauth2/token", "registration_endpoint": origin + "/oauth2/register",
            "response_types_supported": ["code"], "grant_types_supported": ["authorization_code", "refresh_token"],
            "token_endpoint_auth_methods_supported": ["client_secret_post", "none"],
            "code_challenge_methods_supported": ["S256"], "scopes_supported": sorted(_MCP_SCOPES)}


@router.post("/oauth2/register")
async def register_mcp_client(body: dict, session: AsyncSession = Depends(get_oauth_session)):
    redirects = body.get("redirect_uris")
    name = body.get("client_name", "MCP client")
    scope = body.get("scope", "profile read:tasks read:projects read:requirements")
    grants = body.get("grant_types", ["authorization_code", "refresh_token"])
    responses = body.get("response_types", ["code"])
    method = body.get("token_endpoint_auth_method", "client_secret_post")
    if not isinstance(redirects, list) or not 1 <= len(redirects) <= 20:
        return JSONResponse(status_code=400, content={"error": "invalid_redirect_uri"})
    for redirect in redirects:
        if not isinstance(redirect, str):
            return JSONResponse(status_code=400, content={"error": "invalid_redirect_uri"})
        try:
            parsed = urlsplit(redirect)
            valid = (len(redirect) <= 2048 and "," not in redirect
                     and not any(ord(c) < 32 or ord(c) == 127 for c in redirect)
                     and parsed.scheme in ("https", "http") and parsed.hostname
                     and not parsed.username and not parsed.password and not parsed.fragment and parsed.port != 0)
        except (ValueError, TypeError):
            valid = False
        if not valid:
            return JSONResponse(status_code=400, content={"error": "invalid_redirect_uri"})
    if (not isinstance(name, str) or not name.strip() or len(name) > 255
            or not isinstance(scope, str) or len(scope) > 512 or not scope.split()
            or not set(scope.split()).issubset(_MCP_SCOPES)
            or not isinstance(grants, list) or not all(isinstance(item, str) for item in grants)
            or "authorization_code" not in grants or not set(grants).issubset({"authorization_code", "refresh_token"})
            or responses != ["code"] or method not in ("client_secret_post", "none")):
        return JSONResponse(status_code=400, content={"error": "invalid_client_metadata"})
    await session.execute(text("select pg_advisory_xact_lock(hashtext('opentask_mcp_dcr'))"))
    total = await session.scalar(select(func.count()).select_from(OAuthClient).where(OAuthClient.created_by.is_(None)))
    recent = await session.scalar(select(func.count()).select_from(OAuthClient).where(
        OAuthClient.created_by.is_(None), OAuthClient.created_at >= datetime.utcnow() - timedelta(minutes=1)))
    if total >= _DCR_MAX_CLIENTS or recent >= _DCR_PER_MINUTE:
        return JSONResponse(status_code=429, content={"error": "rate_limited"}, headers={"Cache-Control": "no-store"})
    client_id = "mcp-" + secrets.token_urlsafe(24)
    client, secret = await OAuthClientService(session).register(
        client_id=client_id, name=name, description=None, redirect_uris=redirects,
        scopes=scope.split(), grant_types=grants, created_by=None, token_endpoint_auth_method=method)
    return JSONResponse(status_code=201, headers={"Cache-Control": "no-store", "Pragma": "no-cache"}, content={
        "client_id": client.client_id, **({"client_secret": secret, "client_secret_expires_at": 0} if method == "client_secret_post" else {}),
        "client_id_issued_at": int(client.created_at.timestamp()), "client_name": client.name, "redirect_uris": redirects,
        "grant_types": grants, "response_types": responses, "scope": scope,
        "token_endpoint_auth_method": method})



def _validate_pkce(challenge: Optional[str], method: Optional[str]) -> None:
    if challenge is None and method is None:
        return  # 既有 confidential 客户端兼容；MCP 客户端使用 S256。
    if method != "S256" or challenge is None or not re.fullmatch(r"[A-Za-z0-9_-]{43}", challenge):
        raise HTTPException(status_code=400, detail={"error": "invalid_request"})



def _client_view(client) -> OAuthClientView:
    """client → 视图（不含 secret 明文）"""
    return OAuthClientView(
        client_id=client.client_id,
        name=client.name,
        description=client.description,
        redirect_uris=split_redirect_uris(client.redirect_uris),
        scopes=sorted(split_scopes(client.scopes)),
        grant_types=sorted(split_scopes(client.grant_types)),
        status=client.status,
        secret_prefix=client.client_secret_prefix,
        created_at=client.created_at.isoformat() if client.created_at else "",
    )


def _oauth_error(
    error: str,
    description: str,
    http_status: int = status.HTTP_400_BAD_REQUEST,
) -> JSONResponse:
    """RFC 6749 §5.2 错误形状"""
    return JSONResponse(
        status_code=http_status,
        content=OAuthErrorResponse(error=error, error_description=description).model_dump(),
    )


def _require_admin(current_user: UserModel) -> None:
    """管理端点：仅 admin 角色"""
    if current_user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="需要管理员权限")


# ===== 授权请求（SPA 支撑） =====


@router.get(
    "/api/oauth2/authorize/context",
    summary="校验授权请求并返回同意页上下文",
)
async def authorize_context(
    client_id: str = Query(..., description="客户端标识"),
    redirect_uri: str = Query(..., description="回调地址"),
    response_type: str = Query("code", description="授权类型（仅 code）"),
    scope: str = Query("", description="请求的 scope（空格分隔）"),
    state: Optional[str] = Query(None, description="客户端自带状态串"),
    code_challenge: Optional[str] = Query(None),
    code_challenge_method: Optional[str] = Query(None),
    resource: Optional[str] = Query(None),
    current_user: UserModel = Depends(authenticate),
    session: AsyncSession = Depends(get_oauth_session),
):
    """同意页展示前调用：校验 client / redirect_uri / scope，并返回展示信息

    校验失败按 RFC 6749 §4.1.2.1 处理：
    - redirect_uri 非法 → **不重定向**，直接 400（防开放重定向）；
    - 其余非法 → 400 + error 字段。
    """
    _validate_pkce(code_challenge, code_challenge_method)
    client_service = OAuthClientService(session)
    try:
        client = await client_service.require_active_client(client_id)
        client_service.verify_redirect_uri(client, redirect_uri)
        if client.created_by is None and (code_challenge is None or resource != public_origin() + "/mcp"):
            raise HTTPException(status_code=400, detail={"error": "invalid_request"})
        if response_type != "code":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"error": "unsupported_response_type"},
            )
        scope = client_service.verify_scope(client, scope)
    except ClientNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "invalid_client", "error_description": str(exc)},
        )
    except RedirectUriError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "invalid_redirect_uri", "error_description": str(exc)},
        )
    except ScopeError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "invalid_scope", "error_description": str(exc)},
        )

    from urllib.parse import urlparse

    return success_response(
        data=AuthorizeContextView(
            client_id=client.client_id,
            client_name=client.name,
            client_description=client.description,
            scope=sorted(split_scopes(scope)),
            redirect_uri=redirect_uri,
            redirect_host=urlparse(redirect_uri).netloc,
            state=state,
            code_challenge=code_challenge,
            code_challenge_method=code_challenge_method,
            resource=resource,
        )
    )


@router.post(
    "/api/oauth2/authorize/approve",
    summary="同意/拒绝授权",
)
async def authorize_decision(
    body: AuthorizeDecisionRequest,
    current_user: UserModel = Depends(authenticate),
    session: AsyncSession = Depends(get_oauth_session),
):
    """同意 → 签发授权码并返回应跳转 URL；拒绝 → 返回带 error 的跳转 URL

    此处**重新校验**全部参数（不信任前端回传），授权码 10 分钟 TTL、一次性消费。
    """
    _validate_pkce(body.code_challenge, body.code_challenge_method)
    client_service = OAuthClientService(session)
    try:
        client = await client_service.require_active_client(body.client_id)
        client_service.verify_redirect_uri(client, body.redirect_uri)
        if client.created_by is None and (body.code_challenge is None or body.resource != public_origin() + "/mcp"):
            raise HTTPException(status_code=400, detail={"error": "invalid_request"})
        scope = client_service.verify_scope(client, body.scope)
    except ClientNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "invalid_client", "error_description": str(exc)},
        )
    except RedirectUriError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "invalid_redirect_uri", "error_description": str(exc)},
        )
    except ScopeError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "invalid_scope", "error_description": str(exc)},
        )

    params = {}
    if body.state:
        params["state"] = body.state

    if body.decision != "approve":
        params["error"] = "access_denied"
        separator = "&" if "?" in body.redirect_uri else "?"
        return success_response(
            data=AuthorizeDecisionResponse(
                redirect_to=f"{body.redirect_uri}{separator}{urlencode(params)}"
            )
        )

    code_service = AuthorizationCodeService(session)
    code = await code_service.issue(
        client_id=client.client_id,
        user_id=str(current_user.id),
        redirect_uri=body.redirect_uri,
        scope=scope,
        code_challenge=body.code_challenge,
        resource=body.resource,
    )
    params["code"] = code
    separator = "&" if "?" in body.redirect_uri else "?"
    return success_response(
        data=AuthorizeDecisionResponse(
            redirect_to=f"{body.redirect_uri}{separator}{urlencode(params)}"
        )
    )


# ===== token 端点（RFC 6749） =====


@router.post(
    "/oauth2/token",
    response_model=OAuthTokenResponse,
    summary="换取令牌（authorization_code / refresh_token）",
)
async def issue_token(
    grant_type: str = Form(...),
    client_id: str = Form(...),
    client_secret: Optional[str] = Form(None),
    code: Optional[str] = Form(None),
    redirect_uri: Optional[str] = Form(None),
    refresh_token: Optional[str] = Form(None),
    code_verifier: Optional[str] = Form(None),
    resource: Optional[str] = Form(None),
    session: AsyncSession = Depends(get_oauth_session),
):
    """授权码 / refresh token 换令牌

    错误形状按 RFC 6749 §5.2：``{error, error_description}``。
    """
    client_service = OAuthClientService(session)
    try:
        client = await client_service.require_active_client(client_id)
        if client.token_endpoint_auth_method == "none":
            if client.created_by is not None or client_secret:
                raise ClientSecretError("公共客户端认证方式不匹配")
        else:
            client_service.verify_secret(client, client_secret)
        client_service.verify_grant_type(client, grant_type)
    except ClientNotFoundError as exc:
        return _oauth_error("invalid_client", str(exc), status.HTTP_401_UNAUTHORIZED)
    except ClientSecretError as exc:
        return _oauth_error("invalid_client", str(exc), status.HTTP_401_UNAUTHORIZED)
    except GrantTypeError as exc:
        return _oauth_error("unsupported_grant_type", str(exc))

    token_service = OAuthTokenService(session)

    if grant_type == "authorization_code":
        if not code:
            return _oauth_error("invalid_request", "缺少 code")
        code_service = AuthorizationCodeService(session)
        try:
            record = await code_service.consume(code=code, client_id=client_id,
                                                code_verifier=code_verifier, redirect_uri=redirect_uri, resource=resource)
        except InvalidGrantError as exc:
            # 重放：授权码已被消费过 → 吊销该用户全部活跃 OAuth token
            existing = await code_service.find(code)
            if code_service.is_replay(existing):
                await token_service.revoke_all_for_user(existing.user_id)
                logger.warning(
                    f"检测到 OAuth 授权码重放: client={client_id} user={existing.user_id}，"
                    "已吊销该用户全部 OAuth 令牌"
                )
            return _oauth_error("invalid_grant", str(exc))
        if redirect_uri and record.redirect_uri != redirect_uri:
            return _oauth_error("invalid_grant", "redirect_uri 与授权请求不一致")

        from opentask.services.oauth2.identity_service import OAuthIdentityService

        identity = OAuthIdentityService(session)
        user = await identity.find_by_id(record.user_id)
        if user is None:
            return _oauth_error("invalid_grant", "授权用户不存在")
        pair = await token_service.issue(
            user=user, client_id=client_id, scope=record.scope, resource=record.resource
        )
        return OAuthTokenResponse(**pair)

    if grant_type == "refresh_token":
        if not refresh_token:
            return _oauth_error("invalid_request", "缺少 refresh_token")
        from opentask.services.oauth2.identity_service import OAuthIdentityService

        identity = OAuthIdentityService(session)
        record = await token_service._find_refresh(refresh_token)
        user = await identity.find_by_id(record.user_id) if record else None
        if record and record.resource != resource:
            return _oauth_error("invalid_target", "resource 与授权请求不一致")
        if user is None:
            return _oauth_error("invalid_grant", "refresh_token 无效")
        try:
            pair = await token_service.rotate_refresh(
                refresh_plain=refresh_token, client_id=client_id, user=user
            )
        except ReplayDetectedError as exc:
            return _oauth_error("invalid_grant", str(exc))
        except InvalidTokenError as exc:
            return _oauth_error("invalid_grant", str(exc))
        return OAuthTokenResponse(**pair)

    return _oauth_error("unsupported_grant_type", f"不支持的 grant_type: {grant_type}")


# ===== userinfo =====


@router.get(
    "/oauth2/userinfo",
    response_model=OAuthUserInfo,
    summary="用户信息",
)
async def userinfo(
    payload_and_user: tuple[dict, UserModel] = Depends(require_oauth_scope("profile")),
):
    """返回代表用户的基础信息

    ``email`` 为**外部传入的原始 email**（OpenTask user 表无 email 列，
    email 作为 username 种子落库，见 spec §6）。
    """
    payload, user = payload_and_user
    return OAuthUserInfo(
        sub=str(user.id),
        username=user.username,
        name=user.name,
        email=user.username,
    )


# ===== revoke（RFC 7009） =====


@router.post(
    "/oauth2/revoke",
    summary="吊销令牌",
)
async def revoke_token(
    body: OAuthRevokeRequest,
    session: AsyncSession = Depends(get_oauth_session),
):
    """吊销令牌——**始终 200**，不泄露令牌是否存在（RFC 7009）"""
    client_service = OAuthClientService(session)
    try:
        client = await client_service.require_active_client(body.client_id)
        client_service.verify_secret(client, body.client_secret)
    except (ClientNotFoundError, ClientSecretError) as exc:
        # 客户端凭证错误必须报错（否则任何人都能吊销他人令牌）
        return _oauth_error("invalid_client", str(exc), status.HTTP_401_UNAUTHORIZED)

    token_service = OAuthTokenService(session)
    await token_service.revoke_by_token(token=body.token, client_id=body.client_id)
    return success_response(data=None, message="已吊销")


# ===== client 注册管理 =====


@router.get(
    "/api/oauth2/clients",
    summary="列出 OAuth client",
)
async def list_clients(
    current_user: UserModel = Depends(authenticate),
    session: AsyncSession = Depends(get_oauth_session),
):
    """列出全部 client（**不含 secret 明文**）"""
    _require_admin(current_user)
    clients = await OAuthClientService(session).list_clients()
    return success_response(data=[_client_view(client) for client in clients])


@router.post(
    "/api/oauth2/clients",
    summary="注册 OAuth client",
)
async def register_client(
    body: OAuthClientCreate,
    current_user: UserModel = Depends(authenticate),
    session: AsyncSession = Depends(get_oauth_session),
):
    """注册 client——**client_secret 明文仅此一次返回**"""
    _require_admin(current_user)
    try:
        client, secret = await OAuthClientService(session).register(
            client_id=body.client_id,
            name=body.name,
            description=body.description,
            redirect_uris=body.redirect_uris,
            scopes=body.scopes,
            grant_types=body.grant_types,
            created_by=str(current_user.id),
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    return success_response(
        data=OAuthClientCreated(client=_client_view(client), client_secret=secret)
    )


@router.patch(
    "/api/oauth2/clients/{client_id}",
    summary="更新 OAuth client",
)
async def update_client(
    client_id: str,
    body: OAuthClientUpdate,
    current_user: UserModel = Depends(authenticate),
    session: AsyncSession = Depends(get_oauth_session),
):
    """更新 client 元信息"""
    _require_admin(current_user)
    try:
        client = await OAuthClientService(session).update(
            client_id,
            name=body.name,
            description=body.description,
            redirect_uris=body.redirect_uris,
            scopes=body.scopes,
            status=body.status,
        )
    except ClientNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    return success_response(data=_client_view(client))


@router.post(
    "/api/oauth2/clients/{client_id}/rotate-secret",
    summary="轮换 client secret",
)
async def rotate_client_secret(
    client_id: str,
    current_user: UserModel = Depends(authenticate),
    session: AsyncSession = Depends(get_oauth_session),
):
    """轮换 client secret——**新明文仅此一次返回**"""
    _require_admin(current_user)
    try:
        client, secret = await OAuthClientService(session).rotate_secret(client_id)
    except ClientNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except ClientSecretError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    return success_response(
        data=OAuthClientCreated(client=_client_view(client), client_secret=secret)
    )


@router.delete(
    "/api/oauth2/clients/{client_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="删除 OAuth client",
)
async def delete_client(
    client_id: str,
    current_user: UserModel = Depends(authenticate),
    session: AsyncSession = Depends(get_oauth_session),
):
    """删除 client（级联清理其授权码与令牌）"""
    _require_admin(current_user)
    try:
        await OAuthClientService(session).delete(client_id)
    except ClientNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    return None
