"""OAuth2 令牌服务（access token 签发 / refresh 轮换 / 吊销 / 校验内核）

access token 形态：**复用既有 JWT 机制**（HS256 + `AUTH_SECRET_KEY`），
claims 定稿见 docs/superpowers/specs/2026-11-02-oauth2-provider-design.md：

    sub(用户 ID) + tv(token_version) + aud(client_id) + scope(空格分隔) + jti + exp

**为什么带 `aud`**：python-jose 3.5.0 在 `jwt.decode` 不传 `audience=` 时，
对带 `aud` claim 的 token 直接抛 `JWTError: Invalid audience`。既有
`jwt_utils.verify_token` 正是这种调用，因此带 `aud` 的 OAuth token 天然进不了
全局鉴权链（`/api/*`）与契约层（`/tasks`）——只读 scope 形同虚设的风险为零，
既有 `auth.py` / `jwt_utils.py` 零改动。该库行为由
`backend/tests/oauth2/test_scope_enforcement.py` 钉死为回归测试。

**为什么 scope 不叫 scp**：`scp` 已被 OpenTask 内部受限令牌占用
（`auth.py` 精确判 `scp == "pwd_change"`），语义互斥，OAuth scope 走 `scope` claim。
"""

import hashlib
import logging
import secrets
import uuid
from datetime import datetime, timedelta
from typing import Optional

from jose import JWTError, jwt
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from opentask.config import config
from opentask.jwt_utils import ALGORITHM, SECRET_KEY
from opentask.models.oauth2.model import (
    OAuthAccessToken,
    OAuthRefreshToken,
)
from opentask.models.user.model import UserModel

logger = logging.getLogger(__name__)


class TokenRevokedError(Exception):
    """令牌已被吊销"""


class InvalidTokenError(Exception):
    """令牌无效（签名/claims 不合规）"""


class InsufficientScopeError(Exception):
    """令牌 scope 不足"""


class ReplayDetectedError(Exception):
    """refresh token 重放（已吊销的 token 被再次使用）"""


def hash_token(token: str) -> str:
    """明文 token → SHA-256 十六进制哈希"""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


class OAuthTokenService:
    """OAuth 令牌签发与校验"""

    def __init__(self, session: AsyncSession):
        self.session = session

    # ---- 签发 ----

    async def issue(
        self,
        *,
        user: UserModel,
        client_id: str,
        scope: str,
        resource: Optional[str] = None,
        expires_delta: Optional[timedelta] = None,
    ) -> dict:
        """签发 access token + refresh token

        返回 ``{access_token, token_type, expires_in, refresh_token, scope}``。
        access token 是 JWT；refresh token 是随机十六进制串（**明文仅此一次**，
        库中只存哈希）。
        """
        now = datetime.utcnow()
        access_expire = expires_delta or timedelta(minutes=config.access_expire_minutes)
        jti = str(uuid.uuid4())

        access_token = jwt.encode(
            {
                "sub": str(user.id),
                "tv": user.token_version,
                "aud": resource or client_id,
                **({"client_id": client_id} if resource else {}),
                "scope": scope,
                "jti": jti,
                "exp": now + access_expire,
            },
            SECRET_KEY,
            algorithm=ALGORITHM,
        )

        refresh_plain = secrets.token_hex(32)
        self.session.add(
            OAuthAccessToken(
                token_hash=hash_token(jti),
                client_id=client_id,
                user_id=str(user.id),
                scope=scope,
                expires_at=now + access_expire,
                revoked_at=None,
                created_at=now,
            )
        )
        self.session.add(
            OAuthRefreshToken(
                token_hash=hash_token(refresh_plain),
                client_id=client_id,
                user_id=str(user.id),
                scope=scope,
                resource=resource,
                expires_at=now + timedelta(days=config.oauth_refresh_expire_days),
                revoked_at=None,
                rotated_to_hash=None,
                created_at=now,
            )
        )
        await self.session.commit()
        return {
            "access_token": access_token,
            "token_type": "Bearer",
            "expires_in": int(access_expire.total_seconds()),
            "refresh_token": refresh_plain,
            "scope": scope,
        }

    # ---- refresh 轮换 ----

    async def rotate_refresh(
        self,
        *,
        refresh_plain: str,
        client_id: str,
        user: UserModel,
    ) -> dict:
        """refresh token 轮换：签发新对，吊销旧行

        旧行已被吊销却再次出现 → **重放** → 吊销该用户全部活跃 OAuth token
        （疑似泄漏处置），并抛 ReplayDetectedError。
        """
        record = await self._find_refresh(refresh_plain)
        if record is None:
            raise InvalidTokenError("refresh_token 无效")
        if record.client_id != client_id:
            raise InvalidTokenError("refresh_token 与客户端不匹配")
        if record.revoked_at is not None:
            # 重放：已吊销的 refresh 被再次使用
            await self.revoke_all_for_user(record.user_id)
            logger.warning(
                f"检测到 OAuth refresh token 重放: client={client_id} "
                f"user={record.user_id}，已吊销该用户全部 OAuth 令牌"
            )
            raise ReplayDetectedError("refresh_token 已被吊销")
        if record.expires_at < datetime.utcnow():
            raise InvalidTokenError("refresh_token 已过期")

        new_pair = await self.issue(
            user=user, client_id=client_id, scope=record.scope, resource=record.resource
        )
        # 旧行标记轮换并吊销
        record.revoked_at = datetime.utcnow()
        record.rotated_to_hash = hash_token(new_pair["refresh_token"])
        await self.session.commit()
        return new_pair

    async def _find_refresh(self, refresh_plain: str) -> Optional[OAuthRefreshToken]:
        if not refresh_plain:
            return None
        result = await self.session.execute(
            select(OAuthRefreshToken).where(
                OAuthRefreshToken.token_hash == hash_token(refresh_plain)
            )
        )
        return result.scalar_one_or_none()

    # ---- 吊销 ----

    async def revoke_access_token_by_jti(self, jti: str) -> bool:
        """按 jti 吊销 access token"""
        result = await self.session.execute(
            update(OAuthAccessToken)
            .where(
                OAuthAccessToken.token_hash == hash_token(jti),
                OAuthAccessToken.revoked_at.is_(None),
            )
            .values(revoked_at=datetime.utcnow())
        )
        return result.rowcount > 0

    async def revoke_all_for_user(self, user_id: str) -> int:
        """吊销该用户全部活跃 OAuth token（access + refresh），返回吊销条数"""
        now = datetime.utcnow()
        access_result = await self.session.execute(
            update(OAuthAccessToken)
            .where(
                OAuthAccessToken.user_id == user_id,
                OAuthAccessToken.revoked_at.is_(None),
            )
            .values(revoked_at=now)
        )
        refresh_result = await self.session.execute(
            update(OAuthRefreshToken)
            .where(
                OAuthRefreshToken.user_id == user_id,
                OAuthRefreshToken.revoked_at.is_(None),
            )
            .values(revoked_at=now)
        )
        await self.session.commit()
        return (access_result.rowcount or 0) + (refresh_result.rowcount or 0)

    async def revoke_by_token(self, *, token: str, client_id: str) -> bool:
        """RFC 7009 吊销：按 access token JWT 的 jti 或 refresh token 明文吊销

        始终返回「是否命中」，但调用方对外应统一回 200（不泄露 token 是否存在）。
        """
        if not token:
            return False
        # 先按 refresh token 明文匹配
        record = await self._find_refresh(token)
        if record is not None and record.client_id == client_id:
            record.revoked_at = datetime.utcnow()
            await self.session.commit()
            return True
        # 再按 access token JWT 解析 jti
        try:
            payload = jwt.decode(
                token,
                SECRET_KEY,
                algorithms=[ALGORITHM],
                options={"verify_aud": False},
            )
        except JWTError:
            return False
        jti = payload.get("jti")
        if not jti or (payload.get("client_id") or payload.get("aud")) != client_id:
            return False
        return await self.revoke_access_token_by_jti(jti)

    # ---- 校验内核 ----

    async def verify(
        self,
        *,
        token: str,
        required_scope: Optional[str] = None,
    ) -> tuple[dict, UserModel]:
        """校验 OAuth access token，返回 (payload, 用户)

        校验链：
        1. 签名有效（`verify_aud=False`，因为 aud 由本方法自行比对）；
        2. `aud` 存在且等于某个 ACTIVE client；
        3. `jti` 未被吊销且未过期；
        4. `sub` 用户存在且 `status == 1`（禁用用户失效）；
        5. `tv == user.token_version`（改密/批量吊销失效）；
        6. 若要求 scope，检查 `scope` claim 是否包含。
        """
        try:
            payload = jwt.decode(
                token,
                SECRET_KEY,
                algorithms=[ALGORITHM],
                options={"verify_aud": False},
            )
        except JWTError as exc:
            raise InvalidTokenError(f"令牌无效: {exc}") from exc

        aud = payload.get("aud")
        if not aud:
            raise InvalidTokenError("令牌缺少 aud")

        from opentask.services.oauth2.client_service import OAuthClientService

        client = await OAuthClientService(self.session).get_by_client_id(payload.get("client_id") or aud)
        if client is None or client.status != "ACTIVE":
            raise InvalidTokenError("客户端不存在或已禁用")

        jti = payload.get("jti")
        if not jti:
            raise InvalidTokenError("令牌缺少 jti")
        revoked = await self._is_access_revoked(jti)
        if revoked:
            raise TokenRevokedError("令牌已被吊销")

        sub = payload.get("sub")
        if not sub:
            raise InvalidTokenError("令牌缺少 sub")
        result = await self.session.execute(
            select(UserModel).where(UserModel.id == sub)
        )
        user = result.scalar_one_or_none()
        if user is None:
            raise InvalidTokenError("用户不存在")
        if user.status != 1:
            raise InvalidTokenError("用户已被禁用")
        if payload.get("tv", 0) != user.token_version:
            raise InvalidTokenError("令牌已失效")

        if required_scope:
            granted = set((payload.get("scope") or "").split())
            if required_scope not in granted:
                raise InsufficientScopeError(f"缺少 scope: {required_scope}")

        return payload, user

    async def _is_access_revoked(self, jti: str) -> bool:
        """按 jti 查 access token 登记行：不存在或已吊销即视为失效"""
        result = await self.session.execute(
            select(OAuthAccessToken).where(
                OAuthAccessToken.token_hash == hash_token(jti)
            )
        )
        record = result.scalar_one_or_none()
        if record is None:
            return True
        if record.revoked_at is not None:
            return True
        return record.expires_at < datetime.utcnow()
