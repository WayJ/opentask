"""OAuth2 授权码服务（签发 / 一次性消费 / 重放检测）

口径：
- 授权码明文 `secrets.token_hex(32)`，库中只存 SHA-256 哈希；
- 默认 TTL 10 分钟（config.oauth_code_expire_seconds）；
- **一次性消费**：消费时写 `used_at`；二次使用即视为重放 →
  吊销该用户全部活跃 OAuth token（疑似泄漏处置），并返回 invalid_grant。
"""

import base64
import hashlib
import hmac
import re
import logging
import secrets
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from opentask.config import config
from opentask.models.oauth2.model import OAuthAuthorizationCode

logger = logging.getLogger(__name__)


class InvalidGrantError(Exception):
    """授权码无效/过期/已用过"""


class AuthorizationCodeService:
    """授权码签发与消费"""

    def __init__(self, session: AsyncSession):
        self.session = session

    @staticmethod
    def hash_code(code: str) -> str:
        """授权码明文 → SHA-256 哈希"""
        return hashlib.sha256(code.encode("utf-8")).hexdigest()

    async def issue(
        self,
        *,
        client_id: str,
        user_id: str,
        redirect_uri: str,
        scope: str,
        code_challenge: Optional[str] = None,
        resource: Optional[str] = None,
    ) -> str:
        """签发授权码，返回明文（仅此一次下发给用户端）"""
        code_plain = secrets.token_hex(32)
        now = datetime.utcnow()
        record = OAuthAuthorizationCode(
            code_hash=self.hash_code(code_plain),
            client_id=client_id,
            user_id=user_id,
            redirect_uri=redirect_uri,
            scope=scope,
            code_challenge=code_challenge,
            resource=resource,
            expires_at=now + timedelta(seconds=config.oauth_code_expire_seconds),
            used_at=None,
            created_at=now,
        )
        self.session.add(record)
        await self.session.commit()
        logger.info(f"已签发 OAuth 授权码: client={client_id} user={user_id}")
        return code_plain

    async def find(self, code: str) -> Optional[OAuthAuthorizationCode]:
        """按明文授权码查记录（哈希匹配）"""
        if not code:
            return None
        result = await self.session.execute(
            select(OAuthAuthorizationCode).where(
                OAuthAuthorizationCode.code_hash == self.hash_code(code)
            )
        )
        return result.scalar_one_or_none()

    async def consume(
        self,
        *,
        code: str,
        client_id: str,
        code_verifier: Optional[str] = None,
        redirect_uri: Optional[str] = None,
        resource: Optional[str] = None,
    ) -> OAuthAuthorizationCode:
        """消费授权码，返回授权记录

        校验顺序：
        1. 记录存在 → 否则 InvalidGrantError
        2. 属于该 client → 否则 InvalidGrantError
        3. 未过期 → 否则 InvalidGrantError
        4. 未用过 → 否则 InvalidGrantError **且触发重放处置**

        重放处置由调用方（token_service）依据 ``replayed`` 信号执行：
        消费失败时若原记录已 used_at 非空，说明是二次使用。
        """
        record = await self.find(code)
        if record is None:
            raise InvalidGrantError("授权码无效")
        if record.client_id != client_id:
            raise InvalidGrantError("授权码与客户端不匹配")
        if record.expires_at < datetime.utcnow():
            raise InvalidGrantError("授权码已过期")
        if record.used_at is not None:
            # 重放：授权码已被消费过（二次使用）
            raise InvalidGrantError("授权码已被使用")
        if redirect_uri is not None and record.redirect_uri != redirect_uri:
            raise InvalidGrantError("redirect_uri 与授权请求不一致")
        if record.resource != resource:
            raise InvalidGrantError("resource 与授权请求不一致")
        if record.code_challenge is not None:
            if redirect_uri is None or not code_verifier or not re.fullmatch(r"[A-Za-z0-9._~-]{43,128}", code_verifier):
                raise InvalidGrantError("PKCE verifier 无效")
            digest = hashlib.sha256(code_verifier.encode("ascii")).digest()
            challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")
            if not hmac.compare_digest(record.code_challenge, challenge):
                raise InvalidGrantError("PKCE verifier 无效")
        now = datetime.utcnow()
        result = await self.session.execute(
            update(OAuthAuthorizationCode)
            .where(OAuthAuthorizationCode.id == record.id,
                   OAuthAuthorizationCode.used_at.is_(None),
                   OAuthAuthorizationCode.expires_at >= now)
            .values(used_at=now).returning(OAuthAuthorizationCode.id)
        )
        if result.scalar_one_or_none() is None:
            await self.session.rollback()
            raise InvalidGrantError("授权码已被使用或已过期")
        await self.session.commit()
        return record

    @staticmethod
    def is_replay(record: Optional[OAuthAuthorizationCode]) -> bool:
        """判断是否为重放（记录已消费过）"""
        return record is not None and record.used_at is not None
