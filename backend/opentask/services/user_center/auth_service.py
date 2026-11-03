"""本地账号认证服务：登录/锁定/改密（spec 3.2/8）

约定：
- 登录用户名先查 username 列，查不到回退 name 列（兼容存量数据）；
- 密码只存 bcrypt 哈希（password_hash），绝不存明文；
- 连续失败 MAX_FAILED 次锁定 LOCK_MINUTES 分钟，成功登录清零；
- must_change_password 用户登录签发 pwd_change scope 受限 token，
  改密成功后 token_version+1 并吊销全部 refresh，再签发正常 token 对。
"""
import re
from datetime import datetime, timedelta

from fastapi import HTTPException, status
from passlib.context import CryptContext
from sqlalchemy import case, func, update

from opentask.models.user.model import UserModel
from opentask.repositories.base import AsyncSession, NotFoundError
from opentask.repositories.user import UserRepository
from opentask.services.user_center.token_service import TokenService

# 密码哈希上下文（bcrypt），与 opentask.auth 保持一致
_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class AuthService:
    """本地登录 / 账号锁定 / 修改密码"""

    # 连续失败上限，达到即锁定
    MAX_FAILED = 5
    # 锁定时长（分钟）
    LOCK_MINUTES = 15

    def __init__(self, session: AsyncSession):
        self.session = session
        self.user_repo = UserRepository()
        self.token_service = TokenService(session)

    async def _find_user_by_login_name(self, username: str):
        """按登录名查用户：先 username 列，回退 name 列（兼容存量数据）"""
        user = await self.user_repo.get_by_username(self.session, username)
        if user is not None:
            return user
        try:
            return await self.user_repo.get_by_name(self.session, username)
        except NotFoundError:
            return None

    async def login_local(
        self,
        username: str,
        password: str,
        *,
        user_agent: str | None = None,
        ip: str | None = None,
    ) -> tuple:
        """本地登录，成功返回 (user, token_pair)"""
        user = await self._find_user_by_login_name(username)
        if user is None:
            # 不暴露"用户不存在"，统一为用户名或密码错误
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="用户名或密码错误",
            )

        # 禁用用户在一切校验之前拦截
        if user.status != 1:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="用户已被禁用",
            )

        # 锁定期间即使密码正确也拒绝
        if user.locked_until is not None and user.locked_until > datetime.utcnow():
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="账户已锁定，请稍后重试",
            )

        # 未设置过密码的账号（如纯 SSO 同步用户）不能走本地登录
        if not user.password_hash:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="未设置密码，请联系管理员重置",
            )

        # bcrypt 校验；失败累计 failed_attempts，达到上限锁定
        try:
            correct = _pwd_context.verify(password, user.password_hash)
        except Exception:
            # 哈希格式异常等，视为验证失败
            correct = False

        if not correct:
            # 原子自增失败计数（ORM 读改写会丢并发更新，爆破可超上限）；
            # 达到上限时同一条 UPDATE 内置锁定时间并归零计数（SQL 内表达式均取更新前值）
            attempts = func.coalesce(UserModel.failed_attempts, 0) + 1
            await self.session.execute(
                update(UserModel)
                .where(UserModel.id == user.id)
                .values(
                    failed_attempts=case(
                        (attempts >= self.MAX_FAILED, 0), else_=attempts
                    ),
                    locked_until=case(
                        (attempts >= self.MAX_FAILED,
                         datetime.utcnow() + timedelta(minutes=self.LOCK_MINUTES)),
                        else_=UserModel.locked_until,
                    ),
                )
            )
            await self.session.commit()
            await self.session.refresh(user)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="用户名或密码错误",
            )

        # 成功登录：清零计数与锁定标记（原子 UPDATE），并签发 token 对
        await self.session.execute(
            update(UserModel)
            .where(UserModel.id == user.id)
            .values(
                failed_attempts=0,
                locked_until=None,
                last_login_time=datetime.utcnow(),
            )
        )
        await self.session.commit()
        await self.session.refresh(user)

        # 强制改密用户由 issue_tokens 自动继承 pwd_change scope（只放行改密端点）
        pair = await self.token_service.issue_tokens(
            user, user_agent=user_agent, ip=ip
        )
        return user, pair

    async def change_password(
        self,
        user,
        old_password: str,
        new_password: str,
        *,
        user_agent: str | None = None,
        ip: str | None = None,
    ) -> dict:
        """修改密码：校验旧密 → 写新哈希 → token_version+1 → 吊销全部 refresh → 签发新 token 对

        pwd_change scope 用户的旧密即管理员设置的临时密码，校验方式相同。
        """
        # 旧密校验
        if not user.password_hash:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="未设置密码，请联系管理员重置",
            )
        try:
            old_ok = _pwd_context.verify(old_password, user.password_hash)
        except Exception:
            old_ok = False
        if not old_ok:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="原密码错误",
            )

        # 新密码策略：至少 8 位且同时包含字母和数字
        if len(new_password) < 8 or not (
            re.search(r"[A-Za-z]", new_password) and re.search(r"[0-9]", new_password)
        ):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="新密码至少 8 位，且需同时包含字母和数字",
            )

        # 原子写：新哈希 + 解除强制改密 + token_version 自增（ORM 读改写会丢并发 +1）
        await self.session.execute(
            update(UserModel)
            .where(UserModel.id == user.id)
            .values(
                password_hash=_pwd_context.hash(new_password),
                must_change_password=False,
                token_version=func.coalesce(UserModel.token_version, 0) + 1,
            )
        )
        await self.session.commit()
        # 回读对象：后续 issue_tokens 依赖最新的 token_version/must_change_password
        await self.session.refresh(user)

        # 吊销该用户全部 refresh（含改密前签发的受限 token 对应的 refresh）
        await self.token_service.revoke_all_user_refresh(str(user.id))

        # 签发正常 token 对（无 scp 限制）
        return await self.token_service.issue_tokens(
            user, user_agent=user_agent, ip=ip
        )
