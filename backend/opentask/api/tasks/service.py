"""契约层服务：IssueService 复用 + 契约专属查询/标签辅助

不改造 issue service 本体（sprint D2 + 任务约束"需要动 issue service 本体时先 ask"）：
- _generate_issue_code 的方言覆盖已删除：父类实现已改为应用侧解析
  （方言无关，且容忍非数字后缀），覆写只剩历史价值；契约层改为
  覆盖 create_issue 补并发撞号重试（issue_code 唯一索引）。
- 列表查询（updated_since 游标 + limit/offset + 状态集合过滤）现有
  service 不支持，按 D7"并列、不改造既有接口"原则放在契约层内部实现，
  仍基于 Issue model。
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional, Sequence, Set, Tuple

from sqlalchemy import String, cast, delete, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from opentask.models.issue.model import Issue, IssueTag, IssueTimeline
from opentask.models.issue.schema import IssueCreate
from opentask.models.tag.model import Tag
from opentask.models.user.model import UserModel
from opentask.services.issue_service import IssueService

from .mapping import normalize_updated_since

logger = logging.getLogger(__name__)

# 并发 POST 撞 issue_code 唯一索引时的重试次数（max+1 算法每次重试都会
# 看到对方已提交的行，编号前进；超出次数说明冲突另有成因，按原样抛出）
CREATE_RETRY_ATTEMPTS = 3


def _ilike_escape(*keywords: Optional[str]) -> list[str]:
    """关键字 → ILIKE 模式（%kw%，转义 %/_/\\ 防通配注入）；None/空串丢弃"""
    patterns: list[str] = []
    for kw in keywords:
        if not kw:
            continue
        escaped = (
            kw.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        )
        patterns.append(f"%{escaped}%")
    return patterns


class ContractIssueService(IssueService):
    """契约层 IssueService：并发撞号重试 + 契约专属列表查询，业务逻辑全部复用父类"""

    async def create_issue(
        self,
        data: IssueCreate,
        user_id: str,
        dept_id: str | None = None,
        workspace_id: str | None = None,
    ) -> Issue:
        """创建 Issue（转发 workspace_id；保留 IntegrityError 重试作为兜底）。

        E98：编号仅 KEY-N（行锁 counter）；不再依赖年号 max+1 算法。
        workspace_id 必由调用方可靠解析后传入。
        """
        for attempt in range(1, CREATE_RETRY_ATTEMPTS + 1):
            try:
                return await super().create_issue(
                    data, user_id, dept_id=dept_id, workspace_id=workspace_id
                )
            except IntegrityError as e:
                await self.db.rollback()
                if attempt == CREATE_RETRY_ATTEMPTS:
                    raise
                logger.warning(
                    "issue_code 并发撞唯一索引，重试 %d/%d: %s",
                    attempt,
                    CREATE_RETRY_ATTEMPTS,
                    e.orig,
                )

    async def list_issues_for_contract(
        self,
        *,
        status: Optional[Set[str]] = None,
        assignee_id: Optional[str] = None,
        updated_since: Optional[datetime] = None,
        limit: int = 50,
        offset: int = 0,
        reporter_id: Optional[str] = None,
        issue_codes: Optional[Sequence[str]] = None,
        title_kw: Optional[str] = None,
        desc_kw: Optional[str] = None,
        any_kws: Optional[Sequence[str]] = None,
        order: str = "asc",
    ) -> Tuple[List[Issue], int]:
        """契约列表查询：过滤 + updated_since 游标 + limit/offset 分页

        - status 为 IssueStatus **集合**（非单值）：通用状态过滤按正映射
          集合匹配（如 done → {resolved, closed}），与列表正向展示口径
          一致（单值逆映射只取规范代表，会漏数据）；
        - 游标语义（D10）：updated_at **严格大于** updated_since（排他）——
          恰好等于游标时刻的记录已在上一轮返回，含它会造成重复；
          同一游标重复拉取因此保证零重复。排序 updated_at asc + id asc
          保证分页确定性。
        - S7 Jira 线格式层追加过滤（默认值不变，/tasks 契约行为不受影响）：
          reporter_id（报告人）、issue_codes（按编号精确集合）、
          title_kw/desc_kw/any_kws（标题/描述/任一 ILIKE 关键字，
          来自 JQL summary~/description~/text~ 翻译）、order（updated
          排序方向，Jira 线为 desc；契约 /tasks 保持 asc 缺省）。
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
            query = query.where(cast(Issue.status, String).in_(sorted(status)))
        if assignee_id is not None:
            query = query.where(Issue.assignee_id == assignee_id)
        if reporter_id is not None:
            query = query.where(Issue.reporter_id == reporter_id)
        if issue_codes is not None:
            query = query.where(Issue.issue_code.in_(sorted(set(issue_codes))))
        for kw in _ilike_escape(title_kw):
            query = query.where(Issue.title.ilike(kw))
        for kw in _ilike_escape(desc_kw):
            query = query.where(Issue.description.ilike(kw))
        any_kws = any_kws or ()
        for kw in _ilike_escape(*any_kws):
            # text ~ 语义：标题或描述命中即可
            query = query.where(or_(Issue.title.ilike(kw), Issue.description.ilike(kw)))
        if updated_since is not None:
            query = query.where(Issue.updated_at > normalize_updated_since(updated_since))

        total_result = await self.db.execute(
            select(func.count()).select_from(query.subquery())
        )
        total = total_result.scalar() or 0

        updated_col = (
            Issue.updated_at.desc() if order == "desc" else Issue.updated_at.asc()
        )
        id_col = Issue.id.desc() if order == "desc" else Issue.id.asc()
        query = query.order_by(updated_col, id_col)

        query = query.offset(offset).limit(limit)

        result = await self.db.execute(query)
        return list(result.scalars().all()), total


# ============================================================================
# 标签（labels ↔ tags）辅助
# ============================================================================


async def _resolve_fallback_workspace_id(db: AsyncSession) -> str:
    """Issue 无 workspace_id 时：最早工作区；若库中无工作区则惰性创建 Default。"""
    from datetime import datetime as _dt
    from opentask.models.workspace.model import Workspace

    existing = (
        await db.execute(
            select(Workspace.id).order_by(Workspace.created_at.asc(), Workspace.id.asc()).limit(1)
        )
    ).scalar_one_or_none()
    if existing:
        return str(existing)
    now = _dt.utcnow()
    ws = Workspace(
        name="Default",
        slug=f"default-{now.strftime('%Y%m%d%H%M%S')}",
        description="auto for label sync",
        created_at=now,
        updated_at=now,
    )
    db.add(ws)
    await db.flush()
    return str(ws.id)


async def get_or_create_tag(db: AsyncSession, name: str, *, workspace_id: str) -> Tag:
    """按 (workspace_id, name) 取 Tag，不存在则创建（并发下唯一冲突时回退重查）

    workspace_id 为 keyword-only，强制调用方传入工作区，避免全局标签泄漏。

    不提交：插入经 SAVEPOINT flush（撞唯一约束只回滚到保存点，
    不殃及事务内其他未提交变更），由调用方统一提交——
    sync_issue_labels 因此保持"全成或全不成"的原子性。
    """
    if not workspace_id:
        raise ValueError("workspace_id is required for get_or_create_tag")
    result = await db.execute(
        select(Tag).where(Tag.name == name, Tag.workspace_id == workspace_id)
    )
    tag = result.scalar_one_or_none()
    if tag is not None:
        return tag

    tag = Tag(name=name, workspace_id=workspace_id, color="#3b82f6")
    db.add(tag)
    try:
        async with db.begin_nested():
            await db.flush()  # 拿 id；冲突只回滚保存点
    except IntegrityError:
        # 并发创建撞唯一约束：保存点已回滚，重查取对方已提交的行
        result = await db.execute(
            select(Tag).where(Tag.name == name, Tag.workspace_id == workspace_id)
        )
        tag = result.scalar_one()
    return tag


async def get_tag_ids_by_names(
    db: AsyncSession, names: Sequence[str], *, workspace_id: str
) -> Dict[str, int]:
    """名称 → tag_id 映射（仅返回命中的；工作区内）"""
    if not names:
        return {}
    result = await db.execute(
        select(Tag).where(Tag.name.in_(list(names)), Tag.workspace_id == workspace_id)
    )
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

    issue_row = (
        await service.db.execute(select(Issue).where(Issue.id == issue_id))
    ).scalar_one_or_none()
    if issue_row is None:
        raise ValueError(f"issue not found: {issue_id}")
    workspace_id = issue_row.workspace_id
    if not workspace_id:
        workspace_id = await _resolve_fallback_workspace_id(service.db)

    current = await get_issue_current_tags(service.db, issue_id)  # {name: issue_tag_id}
    current_names = set(current)

    to_remove = sorted(current_names - desired_names)
    to_add = [n for n in desired_list if n not in current_names]

    if not to_remove and not to_add:
        return

    if to_remove:
        tag_ids_by_name = await get_tag_ids_by_names(
            service.db, to_remove, workspace_id=workspace_id
        )
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
        tag = await get_or_create_tag(service.db, name, workspace_id=workspace_id)
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
