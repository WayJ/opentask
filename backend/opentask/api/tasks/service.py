"""契约层服务：IssueService 复用 + 契约专属查询/标签辅助

不改造 issue service 本体（sprint D2 + 任务约束"需要动 issue service 本体时先 ask"）：
- ContractIssueService 仅覆盖 `_generate_issue_code` 的方言差异 —— 父类实现是
  MySQL 原生 SQL（CAST ... AS UNSIGNED），PostgreSQL 上不可用；本实现用
  SQLAlchemy 方言无关表达式，算法与父类一致（当年最大序号 + 1）。
  PG 全局切换 sprint 统一迁移后可删除该覆盖。
- 列表查询（updated_since 游标 + limit/offset）现有 service 不支持，
  按 D7"并列、不改造既有接口"原则放在契约层内部实现，仍基于 Issue model。
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional, Sequence, Set, Tuple

from sqlalchemy import Integer, String, cast, delete, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from opentask.models.issue.model import Issue, IssueTag, IssueTimeline
from opentask.models.tag.model import Tag
from opentask.models.user.model import UserModel
from opentask.services.issue_service import IssueService

from .mapping import normalize_updated_since

logger = logging.getLogger(__name__)


class ContractIssueService(IssueService):
    """契约层 IssueService：仅方言差异覆盖，业务逻辑全部复用父类"""

    async def _generate_issue_code(self) -> str:
        """生成问题编号（与父类同算法，PostgreSQL/MySQL 通用）

        父类版本为 MySQL 原生 SQL（CAST AS UNSIGNED / CHAR_LENGTH 拼接），
        PostgreSQL 无 UNSIGNED 类型会直接报错；此处改用 SQLAlchemy 表达式，
        两种方言下均编译为各自合法 SQL，语义不变：当年最大序号 + 1。
        """
        prefix = f"ISSUE{datetime.now().year}-"
        suffix_num = cast(
            func.substring(Issue.issue_code, func.char_length(prefix) + 1), Integer
        )
        query = select(func.max(suffix_num)).where(
            Issue.issue_code.like(f"{prefix}%")
        )
        result = await self.db.execute(query)
        max_num = result.scalar()
        return f"{prefix}{(max_num or 0) + 1}"

    async def list_issues_for_contract(
        self,
        *,
        status: Optional[str] = None,
        assignee_id: Optional[str] = None,
        updated_since: Optional[datetime] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[List[Issue], int]:
        """契约列表查询：过滤 + updated_since 游标 + limit/offset 分页

        游标语义（D10）：updated_at **严格大于** updated_since（排他）——
        恰好等于游标时刻的记录已在上一轮返回，含它会造成重复；
        同一游标重复拉取因此保证零重复。排序 updated_at asc + id asc
        保证分页确定性。
        """
        query = (
            select(Issue)
            .options(selectinload(Issue.tags))
            .where(Issue.is_deleted == False)  # noqa: E712
        )
        if status is not None:
            # mysql.ENUM 在 PG 上编译为原生枚举类型，直接与 varchar 绑定参数比较
            # 会报 operator does not exist；cast 成文本比较，两种方言均合法
            # （PG 全局切换 sprint 迁移模型时可 revisit 索引友好写法）
            query = query.where(cast(Issue.status, String) == status)
        if assignee_id is not None:
            query = query.where(Issue.assignee_id == assignee_id)
        if updated_since is not None:
            query = query.where(Issue.updated_at > normalize_updated_since(updated_since))

        total_result = await self.db.execute(
            select(func.count()).select_from(query.subquery())
        )
        total = total_result.scalar() or 0

        query = query.order_by(Issue.updated_at.asc(), Issue.id.asc())
        query = query.offset(offset).limit(limit)

        result = await self.db.execute(query)
        return list(result.scalars().all()), total


# ============================================================================
# 标签（labels ↔ tags）辅助
# ============================================================================

async def get_or_create_tag(db: AsyncSession, name: str) -> Tag:
    """按名称取 Tag，不存在则创建（并发下唯一冲突时回退重查）"""
    result = await db.execute(select(Tag).where(Tag.name == name))
    tag = result.scalar_one_or_none()
    if tag is not None:
        return tag

    tag = Tag(name=name)
    db.add(tag)
    try:
        await db.commit()
    except IntegrityError:
        # 并发创建撞唯一约束：回退查已存在行
        await db.rollback()
        result = await db.execute(select(Tag).where(Tag.name == name))
        tag = result.scalar_one()
    await db.refresh(tag)
    return tag


async def get_tag_ids_by_names(db: AsyncSession, names: Sequence[str]) -> Dict[str, int]:
    """名称 → tag_id 映射（仅返回命中的）"""
    if not names:
        return {}
    result = await db.execute(select(Tag).where(Tag.name.in_(list(names))))
    return {t.name: t.id for t in result.scalars().all()}


async def sync_issue_labels(
    service: IssueService,
    issue_id: str,
    desired: Sequence[str],
    user_id: str | None = None,
) -> None:
    """把 issue 的标签对齐为 desired（差量增删，写 LABEL_ADDED/LABEL_REMOVED timeline）

    注意：不走 IssueService.add_tag/remove_tag —— 现有 add_tag 存在既有缺陷
    （调用 _add_timeline 缺 user_id 位置参数，UI 路径同样会 500，属 issue service
    本体问题，按任务约束不在本 sprint 修复）；此处按相同语义直接写
    IssueTag + IssueTimeline（action_type/action_data 与 service 保持一致，
    并正确带上 user_id），单次 commit。
    """
    desired_list = list(dict.fromkeys(desired))
    desired_names = set(desired_list)

    current = await get_issue_current_tags(service.db, issue_id)  # {name: issue_tag_id}
    current_names = set(current)

    to_remove = sorted(current_names - desired_names)
    to_add = [n for n in desired_list if n not in current_names]

    if not to_remove and not to_add:
        return

    if to_remove:
        tag_ids_by_name = await get_tag_ids_by_names(service.db, to_remove)
        remove_tag_ids = [tag_ids_by_name[n] for n in to_remove if n in tag_ids_by_name]
        await service.db.execute(
            delete(IssueTag).where(
                IssueTag.issue_id == issue_id, IssueTag.tag_id.in_(remove_tag_ids)
            )
        )
        for name in to_remove:
            if name in tag_ids_by_name:
                service.db.add(
                    IssueTimeline(
                        issue_id=issue_id,
                        user_id=user_id,
                        action_type="label_removed",
                        action_data={"tag_id": tag_ids_by_name[name], "label": name},
                    )
                )

    for name in to_add:
        tag = await get_or_create_tag(service.db, name)
        service.db.add(IssueTag(issue_id=issue_id, tag_id=tag.id))
        service.db.add(
            IssueTimeline(
                issue_id=issue_id,
                user_id=user_id,
                action_type="label_added",
                action_data={"tag_id": tag.id, "label": name},
            )
        )

    await service.db.commit()


async def get_issue_current_tags(
    db: AsyncSession, issue_id: str
) -> Dict[str, int]:
    """issue 当前标签：{标签名: issue_tag 行 id}（用于差量同步）"""
    result = await db.execute(
        select(IssueTag.id, Tag.name)
        .join(Tag, IssueTag.tag_id == Tag.id)
        .where(IssueTag.issue_id == issue_id)
    )
    return {name: it_id for it_id, name in result.all()}


# ============================================================================
# 用户展示名批量预取（metadata.username）
# ============================================================================

async def get_usernames_by_ids(
    db: AsyncSession, user_ids: Sequence[str]
) -> Dict[str, str]:
    """user_id → 展示名（username 优先，回退 name）"""
    unique_ids = {str(u) for u in user_ids if u}
    if not unique_ids:
        return {}
    result = await db.execute(
        select(UserModel.id, UserModel.username, UserModel.name).where(
            UserModel.id.in_(list(unique_ids))
        )
    )
    return {
        str(uid): (username or name or str(uid))
        for uid, username, name in result.all()
    }
