"""AccessToken 服务"""
import hashlib
import logging
import secrets
from datetime import datetime, timedelta
from typing import Optional

from fastapi import HTTPException
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from opentask.models.access_token.model import AccessToken
from opentask.models.access_token.schema import (
    AccessTokenCreate,
    AccessTokenResponse,
    AccessTokenCreateResponse,
)
from opentask.models.user.model import UserModel

logger = logging.getLogger(__name__)

# Access Token 配置
TOKEN_PREFIX = "vk_"
TOKEN_BYTES = 32  # 生成 32 字节随机 token
DEFAULT_EXPIRE_DAYS = 365  # 默认 1 年有效期


class AccessTokenService:
    """用户 Access Token 服务"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, user_id: str, dto: AccessTokenCreate) -> tuple[AccessToken, str]:
        """
        创建 Access Token

        Args:
            user_id: 用户 ID
            dto: 创建 DTO

        Returns:
            (token_model, raw_token) - 模型对象和原始 token（仅此一次返回）
        """
        # 生成随机 token
        raw_token = TOKEN_PREFIX + secrets.token_hex(TOKEN_BYTES)

        # 计算 SHA-256 哈希
        token_hash = self._hash_token(raw_token)

        # 提取前缀用于显示 (vk_ + 前4位)
        token_prefix = raw_token[:7]  # e.g. "vk_a1b2"

        now = datetime.utcnow()
        expires_at = now + timedelta(days=DEFAULT_EXPIRE_DAYS)

        access_token = AccessToken(
            user_id=user_id,
            name=dto.name,
            description=dto.description,
            token_hash=token_hash,
            token_prefix=token_prefix,
            expires_at=expires_at,
            created_at=now,
            updated_at=now,
        )
        self.db.add(access_token)
        await self.db.commit()
        await self.db.refresh(access_token)

        logger.info(f"Created access token for user {user_id}: {dto.name} ({token_prefix}...)")
        return access_token, raw_token

    async def get_list(self, user_id: str) -> list[AccessToken]:
        """
        获取用户的所有 Access Token

        Args:
            user_id: 用户 ID

        Returns:
            Token 列表
        """
        result = await self.db.execute(
            select(AccessToken)
            .where(AccessToken.user_id == user_id)
            .order_by(AccessToken.created_at.desc())
        )
        return list(result.scalars().all())

    async def delete(self, token_id: str, user_id: str) -> None:
        """
        删除 Access Token

        Args:
            token_id: Token ID
            user_id: 用户 ID
        """
        token = await self._get_by_id(token_id, user_id)
        if not token:
            raise HTTPException(status_code=404, detail="Token 不存在")

        await self.db.delete(token)
        await self.db.commit()
        logger.info(f"Deleted access token {token_id} for user {user_id}")

    async def validate_token(self, raw_token: str) -> Optional[UserModel]:
        """
        验证 Access Token 并返回关联用户

        Args:
            raw_token: 原始 token 值

        Returns:
            关联的用户对象，验证失败返回 None
        """
        if not raw_token.startswith(TOKEN_PREFIX):
            return None

        token_hash = self._hash_token(raw_token)

        result = await self.db.execute(
            select(AccessToken).where(AccessToken.token_hash == token_hash)
        )
        token = result.scalar_one_or_none()

        if not token:
            return None

        # 检查是否过期
        if token.expires_at and datetime.utcnow() > token.expires_at:
            logger.info(f"Access token expired: {token.token_prefix}...")
            return None

        # 更新最后使用时间（异步，不阻塞）
        token.last_used_at = datetime.utcnow()
        token.updated_at = datetime.utcnow()
        await self.db.commit()

        # 获取关联用户
        result = await self.db.execute(
            select(UserModel).where(UserModel.id == token.user_id)
        )
        user = result.scalar_one_or_none()

        if user and user.status != 1:
            return None

        return user

    async def _get_by_id(self, token_id: str, user_id: str) -> Optional[AccessToken]:
        """根据 ID 获取 Token"""
        result = await self.db.execute(
            select(AccessToken).where(
                and_(AccessToken.id == token_id, AccessToken.user_id == user_id)
            )
        )
        return result.scalar_one_or_none()

    @staticmethod
    def _hash_token(raw_token: str) -> str:
        """计算 token 的 SHA-256 哈希"""
        return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()

    def to_response(self, token: AccessToken) -> AccessTokenResponse:
        """转换为响应对象（不含完整 token）"""
        return AccessTokenResponse(
            id=str(token.id),
            user_id=token.user_id,
            name=token.name,
            description=token.description,
            token_prefix=token.token_prefix,
            expires_at=token.expires_at,
            last_used_at=token.last_used_at,
            created_at=token.created_at,
            updated_at=token.updated_at,
        )

    def to_create_response(self, token: AccessToken, raw_token: str) -> AccessTokenCreateResponse:
        """转换为创建响应对象（含完整 token）"""
        resp = self.to_response(token)
        return AccessTokenCreateResponse(
            **resp.model_dump(),
            token=raw_token,
        )
