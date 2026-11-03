"""SSO 存量用户迁移服务（Phase 2 Task 3）

目标：把从未设置过本地密码的存量用户（password_hash 为空，含 SSO 同步用户
和 username 为空的老用户）批量迁移为可本地登录的账号：
- username 为空的按 sso_account → name → user_<id前8> 回填；
- 生成 12 位随机临时密码，bcrypt 哈希后写 password_hash；
- 置 must_change_password=True，下次登录强制改密。

范围排除：钉钉用户（password_hash 为空但 dingtalk_user_id 非空）不迁移——
钉钉同步/免登用户走钉钉通道，无本地密码语义，CSV 中也不会出现。

安全约定：
- 临时密码只出现在返回给管理员的响应体（CSV 文本供下载分发），
  绝不 print / logger 落盘；
- 幂等：已有 password_hash 的用户直接跳过，重跑 migrated=0。

username 回填的 lower 归一化判重手法与 Phase 1 迁移
（alembic 2026_10_23_0001 _backfill_user_data）保持一致：
MySQL 默认 ci collation 的唯一索引不区分大小写，判重必须统一 lower()。
唯一化算法见 services/user_center/utils.py unique_username（公共函数，钉钉同步复用）。
"""
from passlib.context import CryptContext
from sqlalchemy import select

from opentask.models.user.model import UserModel
from opentask.repositories.base import AsyncSession
from opentask.services.user_center.utils import generate_temp_password, unique_username

# 密码哈希上下文（bcrypt），与 auth_service 保持一致
_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class MigrateService:
    """SSO 存量用户迁移"""

    def __init__(self, session: AsyncSession):
        self.session = session

    def _backfill_username(self, user: UserModel, existing: set[str]) -> None:
        """回填 username：sso_account → name → user_<id前8>，大小写唯一化

        existing 为已占用 username 的 lower 归一化集合（含本次已回填的）。
        """
        base = (user.sso_account or "").strip() or (user.name or "").strip()
        if not base:
            # 既无 SSO 账号也无姓名，用主键前 8 位兜底保证非空
            base = f"user_{str(user.id)[:8]}"
        user.username = unique_username(existing, base)
        existing.add(user.username.lower())

    async def migrate_sso_users(self) -> dict:
        """迁移全部无本地密码的存量用户，返回 {migrated, csv}

        钉钉用户（password_hash 为空但 dingtalk_user_id 非空）不在迁移范围：
        他们走钉钉同步/免登通道，无本地密码语义。
        csv 为 "username,temp_password\\n..." 文本（含表头），
        仅供管理员下载分发，不落日志、不落盘；无可迁移用户时 csv 为空串。
        """
        # 1) 扫描从未设置过本地密码的存量用户（含 SSO 用户和 username 为空的老用户）；
        #    排除钉钉用户（dingtalk_user_id 非空）：钉钉同步/免登用户走钉钉通道，
        #    无本地密码语义，不应被塞临时密码 + 强制改密。
        result = await self.session.execute(
            select(UserModel).where(
                ((UserModel.password_hash.is_(None)) | (UserModel.password_hash == "")),
                UserModel.dingtalk_user_id.is_(None),
            )
        )
        users = list(result.scalars().all())
        if not users:
            # 幂等：重跑无待迁移用户
            return {"migrated": 0, "csv": ""}

        # 2) 已占用 username 集合（lower 归一化，与 Phase 1 迁移一致）
        username_rows = await self.session.execute(
            select(UserModel.username).where(
                UserModel.username.isnot(None), UserModel.username != ""
            )
        )
        existing = {row[0].lower() for row in username_rows.all()}

        # 3) 逐个回填 username + 写临时密码哈希 + 强制改密
        csv_lines = ["username,temp_password"]
        for user in users:
            if not (user.username or "").strip():
                self._backfill_username(user, existing)
            # 生成临时密码 → bcrypt 哈希落库（明文只进响应体 CSV）
            temp_password = generate_temp_password()
            user.password_hash = _pwd_context.hash(temp_password)
            user.must_change_password = True
            csv_lines.append(f"{user.username},{temp_password}")

        await self.session.commit()

        # 注意：此处不打印/记录任何临时密码
        return {"migrated": len(users), "csv": "\n".join(csv_lines)}
