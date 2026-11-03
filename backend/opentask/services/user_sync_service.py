"""
用户同步服务

负责同步 SSO 用户到本地数据库
"""
import logging
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from opentask.models.user.model import UserModel
from opentask.models.user.schema import SsoUserInfo

logger = logging.getLogger(__name__)


async def sync_or_create_user(sso_user: SsoUserInfo, session: AsyncSession) -> UserModel:
    """
    同步或创建用户

    策略：
    - 如果本地用户存在（通过 sso_user_id 查找），更新 SSO 字段信息
    - 如果本地用户不存在，创建新用户（默认角色：viewer，默认状态：启用）

    注意：本地管理的字段（status、role）不会被覆盖

    Args:
        sso_user: SSO 用户信息
        session: 数据库会话

    Returns:
        UserModel: 本地用户对象
    """
    sso_user_id = sso_user.userId

    # 1. 查找本地用户（通过 SSO 用户 ID）
    result = await session.execute(
        select(UserModel).where(UserModel.sso_user_id == sso_user_id)
    )
    user = result.scalar_one_or_none()

    if user:
        # 2. 用户存在：更新 SSO 字段（保留本地管理字段）
        logger.info(f"更新 SSO 用户: {sso_user.userAccount} (ID: {user.id})")

        user.sso_account = sso_user.userAccount
        user.sso_name = sso_user.userName
        user.organize_id = sso_user.organizeId
        user.organize_name = sso_user.organizeName
        user.position_id = sso_user.positionId
        user.position_name = sso_user.positionName
        user.last_login_time = datetime.now()
        user.sync_time = datetime.now()

    else:
        # 3. 用户不存在：创建新用户
        logger.info(f"创建新 SSO 用户: {sso_user.userAccount}")

        user = UserModel(
            # SSO 字段
            sso_user_id=sso_user.userId,
            sso_account=sso_user.userAccount,
            sso_name=sso_user.userName,
            organize_id=sso_user.organizeId,
            organize_name=sso_user.organizeName,
            position_id=sso_user.positionId,
            position_name=sso_user.positionName,

            # 本地管理字段（默认值）
            status=1,  # 默认启用
            role="viewer",  # 默认角色

            # 时间字段
            last_login_time=datetime.now(),
            sync_time=datetime.now(),

            # 兼容字段（可为空）
            name=sso_user.userName,
        )
        session.add(user)

    # 4. 提交事务
    await session.commit()
    await session.refresh(user)

    return user


async def get_user_by_sso_id(sso_user_id: str, session: AsyncSession) -> UserModel | None:
    """
    通过 SSO 用户 ID 获取本地用户

    Args:
        sso_user_id: SSO 用户 ID
        session: 数据库会话

    Returns:
        UserModel | None: 用户对象或 None
    """
    result = await session.execute(
        select(UserModel).where(UserModel.sso_user_id == sso_user_id)
    )
    return result.scalar_one_or_none()
