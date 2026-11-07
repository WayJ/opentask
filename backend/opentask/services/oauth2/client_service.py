"""OAuth2 client 注册服务（授权服务器侧的客户端登记）

职责：
- 注册 client（生成 client_secret，**明文仅此一次返回**，库中只存 SHA-256 哈希）；
- 查询/列表（列表**不返回** secret 明文，只返回前缀）；
- 校验 client_secret、redirect_uri 白名单（精确匹配）、scope 允许集、grant_type；
- 禁用 client（禁用后其授权请求与换 token 一律拒绝）。

口径（见 docs/superpowers/specs/2026-11-02-oauth2-provider-design.md）：
- secret 前缀 `ocs_`，与用户 PAT 的 `vk_` 区分，避免误作 Bearer 使用；
- redirect_uri 白名单精确匹配（防开放重定向），不做前缀/通配匹配；
- scope 允许集是**上界**：请求 scope 超出即 invalid_scope，不做隐式收敛。
"""

import hashlib
import logging
import secrets
from datetime import datetime
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from opentask.config import config
from opentask.models.oauth2.model import OAuthClient

logger = logging.getLogger(__name__)

# client_secret 前缀（与用户 PAT 的 vk_ 区分）
CLIENT_SECRET_PREFIX = "ocs_"
# client_secret 随机字节数
CLIENT_SECRET_BYTES = config.oauth_client_secret_bytes
# client_secret 展示前缀长度
CLIENT_SECRET_PREFIX_LEN = 8

# 允许的 grant_type
GRANT_AUTHORIZATION_CODE = "authorization_code"
GRANT_REFRESH_TOKEN = "refresh_token"
DEFAULT_GRANT_TYPES = f"{GRANT_AUTHORIZATION_CODE} {GRANT_REFRESH_TOKEN}"

# client 状态
STATUS_ACTIVE = "ACTIVE"
STATUS_DISABLED = "DISABLED"


def hash_secret(secret: str) -> str:
    """明文 secret → SHA-256 十六进制哈希"""
    return hashlib.sha256(secret.encode("utf-8")).hexdigest()


def generate_client_secret() -> str:
    """生成 client_secret 明文"""
    return CLIENT_SECRET_PREFIX + secrets.token_hex(CLIENT_SECRET_BYTES)


def split_scopes(raw: Optional[str]) -> set[str]:
    """scope 串（空格分隔）→ 集合；去空白、去空项"""
    if not raw:
        return set()
    return {item for item in raw.replace(",", " ").split() if item}


def split_redirect_uris(raw: Optional[str]) -> list[str]:
    """redirect_uri 白名单串（逗号分隔）→ 列表"""
    if not raw:
        return []
    return [item.strip() for item in raw.split(",") if item.strip()]


class ClientNotFoundError(Exception):
    """client 不存在或已被禁用"""


class ClientSecretError(Exception):
    """client_secret 校验失败"""


class RedirectUriError(Exception):
    """redirect_uri 不在白名单"""


class ScopeError(Exception):
    """请求的 scope 超出 client 允许集"""


class GrantTypeError(Exception):
    """不支持的 grant_type"""


class OAuthClientService:
    """OAuth client 注册服务"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def register(
        self,
        *,
        client_id: str,
        name: str,
        description: Optional[str],
        redirect_uris: list[str],
        scopes: list[str],
        grant_types: Optional[list[str]] = None,
        created_by: Optional[str],
        token_endpoint_auth_method: str = "client_secret_post",
    ) -> tuple[OAuthClient, str]:
        """注册 client，返回 (模型, client_secret 明文)

        client_secret 明文**只在此刻出现一次**，调用方须立即下发给客户端并
        自负责任存；库中只存 SHA-256 哈希。
        """
        if token_endpoint_auth_method not in {"client_secret_post", "none"} or (
            token_endpoint_auth_method == "none" and created_by is not None
        ):
            raise ValueError("客户端认证方式不支持")
        if not client_id or not client_id.strip():
            raise ValueError("client_id 不能为空")
        if not redirect_uris:
            raise ValueError("redirect_uri 白名单不能为空")

        existing = await self.get_by_client_id(client_id)
        if existing is not None:
            raise ValueError(f"client_id 已存在: {client_id}")

        secret_plain = generate_client_secret()
        now = datetime.utcnow()
        client = OAuthClient(
            client_id=client_id.strip(),
            client_secret_hash=hash_secret(secret_plain),
            client_secret_prefix=secret_plain[:CLIENT_SECRET_PREFIX_LEN] if token_endpoint_auth_method != "none" else "public",
            token_endpoint_auth_method=token_endpoint_auth_method,
            name=name.strip(),
            description=description,
            redirect_uris=",".join(redirect_uris),
            scopes=" ".join(scopes),
            grant_types=" ".join(grant_types) if grant_types else DEFAULT_GRANT_TYPES,
            status=STATUS_ACTIVE,
            created_by=created_by,
            created_at=now,
            updated_at=now,
        )
        self.session.add(client)
        await self.session.commit()
        await self.session.refresh(client)
        logger.info(f"已注册 OAuth client: {client.client_id} (创建人={created_by})")
        return client, secret_plain

    async def get_by_client_id(self, client_id: str) -> Optional[OAuthClient]:
        """按 client_id 查（不过滤状态）"""
        if not client_id:
            return None
        result = await self.session.execute(
            select(OAuthClient).where(OAuthClient.client_id == client_id)
        )
        return result.scalar_one_or_none()

    async def list_clients(self) -> list[OAuthClient]:
        """列出全部 client（按创建时间倒序）"""
        result = await self.session.execute(
            select(OAuthClient).order_by(OAuthClient.created_at.desc())
        )
        return list(result.scalars().all())

    async def require_active_client(self, client_id: str) -> OAuthClient:
        """取 ACTIVE client，不存在/禁用抛 ClientNotFoundError"""
        client = await self.get_by_client_id(client_id)
        if client is None or client.status != STATUS_ACTIVE:
            raise ClientNotFoundError("客户端不存在或已禁用")
        return client

    async def update(
        self,
        client_id: str,
        *,
        name: Optional[str] = None,
        description: Optional[str] = None,
        redirect_uris: Optional[list[str]] = None,
        scopes: Optional[list[str]] = None,
        status: Optional[str] = None,
    ) -> OAuthClient:
        """更新 client 元信息（不涉及 secret 轮换）"""
        client = await self.get_by_client_id(client_id)
        if client is None:
            raise ClientNotFoundError("客户端不存在")
        if name is not None:
            client.name = name.strip()
        if description is not None:
            client.description = description
        if redirect_uris is not None:
            client.redirect_uris = ",".join(redirect_uris)
        if scopes is not None:
            client.scopes = " ".join(scopes)
        if status is not None:
            client.status = status
        client.updated_at = datetime.utcnow()
        await self.session.commit()
        await self.session.refresh(client)
        return client

    async def rotate_secret(self, client_id: str) -> tuple[OAuthClient, str]:
        """轮换 client_secret，返回 (模型, 新明文)"""
        client = await self.get_by_client_id(client_id)
        if client is None:
            raise ClientNotFoundError("客户端不存在")
        if client.token_endpoint_auth_method == "none":
            raise ClientSecretError("公共客户端不使用客户端密钥")
        secret_plain = generate_client_secret()
        client.client_secret_hash = hash_secret(secret_plain)
        client.client_secret_prefix = secret_plain[:CLIENT_SECRET_PREFIX_LEN]
        client.updated_at = datetime.utcnow()
        await self.session.commit()
        await self.session.refresh(client)
        logger.info(f"已轮换 OAuth client secret: {client.client_id}")
        return client, secret_plain

    async def delete(self, client_id: str) -> None:
        """删除 client（级联吊销其授权码与 token）"""
        client = await self.get_by_client_id(client_id)
        if client is None:
            raise ClientNotFoundError("客户端不存在")
        await self.session.delete(client)
        await self.session.commit()

    # ---- 校验 ----

    @staticmethod
    def verify_secret(client: OAuthClient, client_secret: Optional[str]) -> None:
        """校验 client_secret，失败抛 ClientSecretError"""
        if not client_secret:
            raise ClientSecretError("缺少 client_secret")
        if not secrets.compare_digest(
            client.client_secret_hash, hash_secret(client_secret)
        ):
            raise ClientSecretError("client_secret 无效")

    @staticmethod
    def verify_redirect_uri(client: OAuthClient, redirect_uri: Optional[str]) -> None:
        """校验 redirect_uri 在白名单内（精确匹配），失败抛 RedirectUriError"""
        if not redirect_uri:
            raise RedirectUriError("缺少 redirect_uri")
        allowed = split_redirect_uris(client.redirect_uris)
        if redirect_uri not in allowed:
            raise RedirectUriError("redirect_uri 不在白名单内")

    @staticmethod
    def verify_scope(client: OAuthClient, requested: Optional[str]) -> str:
        """校验请求 scope ⊆ client 允许集，返回规范化 scope 串

        失败抛 ScopeError。**不做隐式收敛**——请求超出即拒绝，避免
        「以为授予了其实没授予」的静默降权。
        """
        asked = split_scopes(requested)
        if not asked:
            raise ScopeError("缺少 scope")
        allowed = split_scopes(client.scopes)
        extra = asked - allowed
        if extra:
            raise ScopeError(f"scope 超出授权范围: {' '.join(sorted(extra))}")
        return " ".join(sorted(asked))

    @staticmethod
    def verify_grant_type(client: OAuthClient, grant_type: Optional[str]) -> None:
        """校验 grant_type 被该 client 允许，失败抛 GrantTypeError"""
        if not grant_type:
            raise GrantTypeError("缺少 grant_type")
        allowed = split_scopes(client.grant_types)
        if grant_type not in allowed:
            raise GrantTypeError(f"不支持的 grant_type: {grant_type}")
