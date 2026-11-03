"""钉钉免密登录服务（Phase 4 Task 3）

authCode → userid → 用户详情 → 本地用户定位/自动建号 → 签发 token 对：

1. authCode 换 userid（get_userid_by_code）、拉用户详情（get_user_detail）；
2. 按 dingtalk_user_id 查本地用户：
   - 已存在：status != 1 → 403 用户已被禁用；否则直接 issue_tokens；
   - 不存在且 dingtalk_auto_register=true：建号（建号风格与 sync_service
     _create_user 一致：name/sso_name=钉钉姓名、username 唯一化、
     role=viewer、password_hash=None、部门按 dept_id_list 映射本地
     department 并写 user_dept，主部门取 main_dept_id 或第一个，映射
     不上的部门跳过）→ issue_tokens；
   - 不存在且开关关闭：403 未开通账号，请联系管理员。

测试用 FakeDingTalkClient 注入（接口窄：get_userid_by_code/get_user_detail）。
"""
import logging

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from opentask.config import config
from opentask.models.user.model import UserModel
from opentask.models.user_center.model import Department, UserDept
from opentask.services.user_center.dingtalk.client import DingTalkClient
from opentask.services.user_center.token_service import TokenService
from opentask.services.user_center.utils import unique_username

logger = logging.getLogger(__name__)


class DingTalkOAuthService:
    """钉钉免密登录（authCode 换 userid，本地定位/建号后签发 token）"""

    def __init__(self, session: AsyncSession, client: DingTalkClient):
        self.session = session
        self.client = client
        self.token_service = TokenService(session)

    async def login_by_code(
        self,
        auth_code: str,
        *,
        user_agent: str | None = None,
        ip: str | None = None,
    ) -> tuple[UserModel, dict]:
        """免登码登录，成功返回 (user, token_pair)"""
        userid = await self.client.get_userid_by_code(auth_code)
        detail = await self.client.get_user_detail(userid)
        detail.setdefault("userid", userid)

        user = await self._find_by_dingtalk_id(userid)
        if user is not None:
            if user.status != 1:
                logger.warning(f"钉钉免登拒绝禁用用户: {user.username or user.id}")
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="用户已被禁用",
                )
            pair = await self.token_service.issue_tokens(
                user, user_agent=user_agent, ip=ip
            )
            return user, pair

        if not config.dingtalk_auto_register:
            logger.info(f"钉钉免登未自动建号（开关关闭）: userid={userid}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="未开通账号，请联系管理员",
            )

        user = await self._create_user(detail)
        logger.info(f"钉钉免登自动建号: userid={userid}, username={user.username}")
        pair = await self.token_service.issue_tokens(user, user_agent=user_agent, ip=ip)
        return user, pair

    # ---- 内部 ----

    async def _find_by_dingtalk_id(self, userid: str) -> UserModel | None:
        """按 dingtalk_user_id 查本地用户"""
        result = await self.session.execute(
            select(UserModel).where(UserModel.dingtalk_user_id == userid)
        )
        return result.scalar_one_or_none()

    async def _create_user(self, detail: dict) -> UserModel:
        """自动建号（风格与 sync_service._create_user 一致）"""
        userid = detail["userid"]
        name = detail.get("name") or userid
        # username 唯一化基准：现有全量 username + name（lower 归一化）
        result = await self.session.execute(select(UserModel))
        existing_names = {
            str(v).lower()
            for u in result.scalars().all()
            for v in (u.username, u.name)
            if v
        }
        username = unique_username(existing_names, name)

        user = UserModel(
            name=name,
            username=username,
            sso_name=name,
            password_hash=None,
            role="viewer",
            dingtalk_user_id=userid,
        )
        self.session.add(user)
        await self.session.flush()

        await self._assign_depts(user, detail)
        # 不在此 commit：随后的 issue_tokens 会提交（get_session 兜底提交）
        return user

    async def _assign_depts(self, user: UserModel, detail: dict) -> None:
        """按 detail 的 dept_id_list 映射本地 department，写 user_dept。

        主部门取 main_dept_id（映射不上则第一个）；映射不上的钉钉部门跳过；
        全部映射不上（含无部门）则不写任何 user_dept 行。
        """
        dt_ids = [int(d) for d in (detail.get("dept_id_list") or []) if d]
        if not dt_ids:
            return
        result = await self.session.execute(
            select(Department).where(
                Department.dingtalk_dept_id.in_([str(d) for d in dt_ids])
            )
        )
        mapped = list(result.scalars().all())
        if not mapped:
            return

        main_dt = str(detail.get("main_dept_id") or "")
        primary = next(
            (d for d in mapped if str(d.dingtalk_dept_id) == main_dt),
            mapped[0],
        )
        for d in mapped:
            self.session.add(
                UserDept(
                    user_id=str(user.id),
                    dept_id=str(d.id),
                    is_primary=d is primary,
                )
            )
        await self.session.flush()
