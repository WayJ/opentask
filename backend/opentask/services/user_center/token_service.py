"""token 生命周期管理：access JWT 签发 + refresh token 轮换与吊销（spec 3.2/8）

约定：
- access：JWT（默认 2h，AUTH_ACCESS_EXPIRE_MINUTES 可配），claims 含
  sub=str(user.id)、tv=user.token_version（批量吊销用）、scp 可选（限定用途）；
- refresh：secrets.token_hex(32) 明文只下发给客户端，库中仅存 SHA-256 哈希；
- 轮换：每次刷新签发新 refresh 并吊销旧行；检测到已吊销 token 被重放时，
  吊销该用户全部 refresh（疑似泄漏，强制全端下线）。
"""
import hashlib
import secrets
from datetime import datetime, timedelta

from fastapi import HTTPException
from sqlalchemy import select, update
from starlette.status import HTTP_401_UNAUTHORIZED

from opentask.config import config
from opentask.jwt_utils import create_access_token
from opentask.models.user.model import UserModel
from opentask.models.user_center.model import RefreshToken

# 返回结构：{"token": access JWT, "refreshToken": refresh 明文, "mustChangePassword": bool}
TokenPair = dict


def _hash_token(plain: str) -> str:
    """refresh 明文 → SHA-256 十六进制哈希（64 位，库里唯一索引）"""
    return hashlib.sha256(plain.encode("utf-8")).hexdigest()


class TokenService:
    """access/refresh 双 token 签发、轮换与吊销"""

    def __init__(self, session):
        self.session = session

    async def issue_tokens(
        self,
        user: UserModel,
        *,
        scope: str | None = None,
        user_agent: str | None = None,
        ip: str | None = None,
    ) -> TokenPair:
        """签发 token 对：access JWT（sub/tv/scp）+ refresh（库存哈希）

        scope 未显式指定时按用户状态继承：must_change_password 用户一律签发
        scp=pwd_change 受限 token（login/rotate/SSO 所有签发点统一生效，
        受限 refresh 无法通过轮换洗白出无限制 access）。
        """
        if scope is None and user.must_change_password:
            scope = "pwd_change"

        # access JWT：sub 统一为用户 ID 字符串，tv 绑定 token_version
        payload = {"sub": str(user.id), "tv": user.token_version}
        if scope:
            payload["scp"] = scope
        access = create_access_token(payload)

        # refresh 明文只出现在返回值，落库的是哈希
        refresh_plain = secrets.token_hex(32)
        self.session.add(
            RefreshToken(
                user_id=str(user.id),
                token_hash=_hash_token(refresh_plain),
                expires_at=datetime.utcnow() + timedelta(days=config.refresh_expire_days),
                user_agent=user_agent,
                ip=ip,
            )
        )
        await self.session.commit()

        return {
            "token": access,
            "refreshToken": refresh_plain,
            "mustChangePassword": bool(user.must_change_password),
        }

    async def rotate_refresh(
        self,
        refresh_plain: str,
        *,
        user_agent: str | None = None,
        ip: str | None = None,
    ) -> TokenPair:
        """轮换 refresh：原子吊销旧行 → 签新对（tv 用当前 user.token_version）

        吊销采用条件更新（WHERE revoked_at IS NULL）保证原子性：
        并发两个相同 token 的请求只有一个能抢到（rowcount==1），
        另一个落入"已吊销"分支触发重放全量吊销，无法绕过判定。
        """
        now = datetime.utcnow()

        # 原子条件更新：抢占该 token 的首次使用（不存在或已吊销时 rowcount==0）
        result = await self.session.execute(
            update(RefreshToken)
            .where(RefreshToken.token_hash == _hash_token(refresh_plain), RefreshToken.revoked_at.is_(None))
            .values(revoked_at=now, last_used_at=now)
        )
        if result.rowcount == 0:
            # 回查一次，区分"不存在"与"已被吊销"两态
            row = (
                await self.session.execute(
                    select(RefreshToken).where(RefreshToken.token_hash == _hash_token(refresh_plain))
                )
            ).scalar_one_or_none()
            if row is None:
                raise HTTPException(status_code=HTTP_401_UNAUTHORIZED, detail="refresh token 无效")
            # 重放已吊销 token：疑似泄漏，吊销该用户全部会话
            await self.revoke_all_user_refresh(row.user_id)
            raise HTTPException(
                status_code=HTTP_401_UNAUTHORIZED,
                detail="refresh token 已吊销，检测到重放，该用户全部会话已下线",
            )

        # 抢到后回读该行，校验过期时间（本行已吊销，过期则直接 401）
        row = (
            await self.session.execute(
                select(RefreshToken).where(RefreshToken.token_hash == _hash_token(refresh_plain))
            )
        ).scalar_one()
        if row.expires_at < now:
            raise HTTPException(status_code=HTTP_401_UNAUTHORIZED, detail="refresh token 已过期")

        # 二次查询取用户（模型不做 relationship，避免 greenlet 问题）
        user = (
            await self.session.execute(select(UserModel).where(UserModel.id == row.user_id))
        ).scalar_one_or_none()
        if user is None:
            raise HTTPException(status_code=HTTP_401_UNAUTHORIZED, detail="用户不存在")
        # 禁用用户：签发后禁用的存量 refresh 不允许继续轮换存活（禁用即全端下线）
        if user.status != 1:
            raise HTTPException(status_code=HTTP_401_UNAUTHORIZED, detail="用户已被禁用")

        return await self.issue_tokens(user, user_agent=user_agent, ip=ip)

    async def revoke_refresh(self, refresh_plain: str) -> bool:
        """吊销单个 refresh token；不存在或已吊销返回 False"""
        row = (
            await self.session.execute(
                select(RefreshToken).where(RefreshToken.token_hash == _hash_token(refresh_plain))
            )
        ).scalar_one_or_none()
        if row is None or row.revoked_at is not None:
            return False
        row.revoked_at = datetime.utcnow()
        await self.session.commit()
        return True

    async def revoke_all_user_refresh(self, user_id: str) -> int:
        """吊销某用户全部未吊销的 refresh token，返回吊销行数"""
        result = await self.session.execute(
            update(RefreshToken)
            .where(RefreshToken.user_id == user_id, RefreshToken.revoked_at.is_(None))
            .values(revoked_at=datetime.utcnow())
        )
        await self.session.commit()
        return result.rowcount
