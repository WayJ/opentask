"""OAuth2 身份对齐服务（外部 email → OpenTask 本地用户）

口径（裁决 G1，**零 schema 变更**）：
- OpenTask `user` 表**全列无 email**（SSO / 钉钉同步链亦无），
  故 email 不作为独立字段落库，而是**作为 username 的种子**；
- 定位顺序：按 `username` 精确查（lower 归一化）→ 命中即复用；
  未命中则用 `unique_username(existing, email)` 建号（冲突自动 `_2` / `_3`）；
- 建号风格照 `services/user_center/dingtalk/oauth_service.py::_create_user`：
  `name=展示名`、`role=viewer`、`password_hash=None`；
- 已知副作用：若该用户此前经 SSO/钉钉同步建过账号且 `username != email`，
  会另建新账号——OAuth「首次连接自动建号」的常规语义。
"""

import logging
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from opentask.models.user.model import UserModel
from opentask.services.user_center.utils import unique_username

logger = logging.getLogger(__name__)


class OAuthIdentityService:
    """外部身份 → 本地用户定位/建号"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def find_by_username(self, username: str) -> Optional[UserModel]:
        """按 username 精确查（lower 归一化，与 unique_username 的归一口径一致）"""
        if not username:
            return None
        result = await self.session.execute(
            select(UserModel).where(UserModel.username == username.strip().lower())
        )
        return result.scalar_one_or_none()

    async def resolve_or_create(
        self,
        *,
        email: str,
        display_name: Optional[str] = None,
    ) -> tuple[UserModel, bool]:
        """按 email 定位本地用户，不存在则建号

        返回 (用户, 是否新建)。
        """
        email = (email or "").strip().lower()
        if not email:
            raise ValueError("缺少 email")

        existing = await self.find_by_username(email)
        if existing is not None:
            return existing, False

        # username 唯一化基准：现有全量 username + name（lower 归一化）
        result = await self.session.execute(select(UserModel))
        existing_names = {
            str(value).lower()
            for user in result.scalars().all()
            for value in (user.username, user.name)
            if value
        }
        username = unique_username(existing_names, email)
        name = (display_name or "").strip() or email

        user = UserModel(
            name=name,
            username=username,
            sso_name=name,
            password_hash=None,
            role="viewer",
        )
        self.session.add(user)
        await self.session.flush()
        logger.info(f"OAuth 授权自动建号: username={username} name={name}")
        return user, True

    async def find_by_id(self, user_id: str) -> Optional[UserModel]:
        """按 ID 查用户"""
        result = await self.session.execute(
            select(UserModel).where(UserModel.id == user_id)
        )
        return result.scalar_one_or_none()
