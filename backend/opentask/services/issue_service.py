"""Issue 服务层"""
from typing import Optional, List, Tuple, Dict, Any
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, update, delete, or_, and_
from sqlalchemy.orm import selectinload, joinedload

from opentask.models.issue.model import (
    Issue,
    IssueComment,
    IssueRelation,
    IssueTimeline,
    IssueTag,
    IssueReaction,
)
from opentask.models.document.model import Document
from opentask.services.storage.service import get_storage_service
from opentask.models.issue.schema import (
    IssueCreate,
    IssueUpdate,
    IssueBulkUpdate,
    IssueQueryParams,
)
from opentask.models.issue.enums import (
    IssueStatus,
    IssuePriority,
    TimelineAction,
    RelationType,
)
from opentask.services.user_center.rbac_service import RbacService


class IssueService:
    """Issue 服务"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def _generate_issue_code(self) -> str:
        """生成问题编号

        格式: ISSUE + 年份 + 序号
        例如: ISSUE2026-1, ISSUE2026-2

        使用当前年份最大序号 + 1，避免重复
        """
        current_year = datetime.now().year
        prefix = f"ISSUE{current_year}-"

        # 查询当前年份已有的 issue_code，序号最大值在 Python 侧计算。
        # 说明：序号是数字（-9 与 -10），按字符串排序会得到错误的最大值
        # （'ISSUE2026-9' > 'ISSUE2026-10'），且数据库侧 CAST 到整数是
        # 方言相关语法（MySQL 用 SIGNED/UNSIGNED，PG 用 INTEGER），
        # 因此取全量 code 后在应用侧解析，保持方言无关（PG/MySQL 均可用）。
        from sqlalchemy import text
        query = text(
            "SELECT issue_code FROM issues "
            "WHERE issue_code LIKE :prefix_pattern"
        )
        result = await self.db.execute(query, {
            "prefix_pattern": f"{prefix}%"
        })

        max_num = 0
        for (code,) in result:
            suffix = code[len(prefix):]
            try:
                num = int(suffix)
            except (TypeError, ValueError):
                continue
            max_num = max(max_num, num)

        # 生成新的序号
        next_number = max_num + 1

        return f"{prefix}{next_number}"

    # ========================================================================
    # CRUD 操作
    # ========================================================================

    async def get_issues(
        self,
        params: IssueQueryParams,
        visible_dept_ids: set[str] | None = None,
        user_id: str | None = None,
        workspace_id: str | None = None,
        allowed_workspace_ids: list[str] | None = None,
    ) -> Tuple[List[Issue], int]:
        """获取 Issue 列表

        visible_dept_ids: 数据范围可见部门集（None=不过滤，空集=SELF 只见本人）
        user_id: 当前用户 ID（配合可见部门集实现"或本人创建"）
        """
        # 使用 joinedload 预加载用户数据
        query = (
            select(Issue)
            .options(
                joinedload(Issue.assignee),
                joinedload(Issue.reporter),
            )
            .where(Issue.is_deleted == False)
        )

        # 筛选条件
        if params.type:
            query = query.where(Issue.type == params.type)
        if params.status:
            query = query.where(Issue.status == params.status)
        if params.priority:
            query = query.where(Issue.priority == params.priority)
        if params.project_id:
            query = query.where(Issue.project_id == params.project_id)
        if params.assignee_id:
            query = query.where(Issue.assignee_id == params.assignee_id)
        if params.reporter_id:
            query = query.where(Issue.reporter_id == params.reporter_id)
        if params.search:
            search_pattern = f"%{params.search}%"
            query = query.where(
                or_(
                    Issue.title.ilike(search_pattern),
                    Issue.description.ilike(search_pattern),
                )
            )

        # 工作区隔离（E3-S1）
        if workspace_id is not None:
            query = query.where(Issue.workspace_id == workspace_id)
        elif allowed_workspace_ids is not None:
            query = query.where(
                or_(
                    Issue.workspace_id.in_(allowed_workspace_ids),
                    Issue.workspace_id.is_(None),
                )
            )

        # 数据范围过滤（visible_dept_ids=None 时 apply_data_scope 原样返回，旧调用零破坏）
        query = RbacService(session=None).apply_data_scope(
            query,
            visible_dept_ids,
            dept_col=Issue.dept_id,
            creator_col=Issue.created_by,
            user_id=user_id,
        )

        # 获取总数
        count_query = select(func.count()).select_from(query.subquery())
        result = await self.db.execute(count_query)
        total = result.scalar()

        # 排序
        sort_column = getattr(Issue, params.sort_by, Issue.created_at)
        if params.sort_order == "asc":
            query = query.order_by(sort_column.asc())
        else:
            query = query.order_by(sort_column.desc())

        # 分页
        offset = (params.page - 1) * params.page_size
        query = query.offset(offset).limit(params.page_size)

        # 执行查询
        result = await self.db.execute(query)
        issues = result.scalars().all()

        return list(issues), total

    async def get_issue(self, issue_id: str, by_code: bool = False) -> Optional[Issue]:
        """获取 Issue 详情

        Args:
            issue_id: Issue ID 或 Issue Code
            by_code: 是否通过 issue_code 查询（默认 False，通过 ID 查询）
        """
        query = (
            select(Issue)
            .options(
                joinedload(Issue.assignee),
                joinedload(Issue.reporter),
                selectinload(Issue.comments),
                selectinload(Issue.relations_as_source),
                selectinload(Issue.relations_as_target),
                selectinload(Issue.timeline),
                selectinload(Issue.tags),
            )
            .where(Issue.is_deleted == False)
        )

        # 根据 by_code 参数选择查询条件
        if by_code:
            query = query.where(Issue.issue_code == issue_id)
        else:
            query = query.where(Issue.id == issue_id)

        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_issues_by_ids(self, issue_ids: List[str]) -> List[Issue]:
        """根据 ID 列表批量获取 Issues

        Args:
            issue_ids: Issue ID 列表

        Returns:
            Issue 列表
        """
        if not issue_ids:
            return []

        # 限制批量查询数量，避免性能问题
        if len(issue_ids) > 100:
            raise ValueError("一次最多查询 100 个 issues")

        query = (
            select(Issue)
            .options(
                joinedload(Issue.assignee),
                joinedload(Issue.reporter),
            )
            .where(Issue.id.in_(issue_ids))
            .where(Issue.is_deleted == False)
            .order_by(Issue.created_at.desc())
        )

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def create_issue(
        self,
        data: IssueCreate,
        user_id: str,
        dept_id: str | None = None,
        workspace_id: str | None = None,
    ) -> Issue:
        """创建 Issue

        dept_id: 创建人主部门 id 快照（None 表示无归属，行保持 NULL）
        workspace_id: 所属工作区（E3-S1）
        """
        # 生成问题编号
        issue_code = await self._generate_issue_code()

        issue_data = data.model_dump()
        issue_data["created_by"] = user_id
        issue_data["updated_by"] = user_id
        issue_data["issue_code"] = issue_code
        issue_data["dept_id"] = dept_id  # 部门归属快照
        issue_data["workspace_id"] = workspace_id

        # 自动设置 reporter_id 为当前用户（如果未提供）
        if not issue_data.get("reporter_id"):
            issue_data["reporter_id"] = user_id

        issue = Issue(**issue_data)
        self.db.add(issue)

        # Flush to get the ID assigned by database
        await self.db.flush()

        # 创建时间线记录
        await self._add_timeline(
            issue_id=issue.id,
            action_type=TimelineAction.CREATED,
            user_id=user_id,
            action_data={"title": issue.title, "type": issue.type.value, "issue_code": issue_code},
        )

        await self.db.commit()
        await self.db.refresh(issue)
        return issue

    async def update_issue(
        self,
        issue_id: str,
        data: IssueUpdate,
        user_id: str,
    ) -> Optional[Issue]:
        """更新 Issue"""
        update_data = data.model_dump(exclude_unset=True)
        if not update_data:
            return await self.get_issue(issue_id)

        update_data["updated_by"] = user_id

        # 记录状态变更
        if "status" in update_data:
            old_status = await self._get_issue_status(issue_id)
            if old_status != update_data["status"]:
                await self._add_timeline(
                    issue_id=issue_id,
                    action_type=TimelineAction.STATUS_CHANGED,
                    user_id=user_id,
                    action_data={
                        "from": old_status,
                        "to": update_data["status"],
                    },
                )

                # 自动设置时间戳
                new_status = IssueStatus(update_data["status"])
                if new_status == IssueStatus.IN_PROGRESS and not update_data.get("started_at"):
                    update_data["started_at"] = datetime.utcnow()
                elif new_status == IssueStatus.RESOLVED:
                    update_data["resolved_at"] = datetime.utcnow()
                elif new_status == IssueStatus.CLOSED:
                    update_data["closed_at"] = datetime.utcnow()

        # 记录优先级变更
        if "priority" in update_data:
            old_priority = await self._get_issue_priority(issue_id)
            if old_priority != update_data["priority"]:
                await self._add_timeline(
                    issue_id=issue_id,
                    action_type=TimelineAction.PRIORITY_CHANGED,
                    user_id=user_id,
                    action_data={
                        "from": old_priority,
                        "to": update_data["priority"],
                    },
                )

        # 记录分配变更
        if "assignee_id" in update_data:
            old_assignee = await self._get_issue_assignee(issue_id)
            if old_assignee != update_data["assignee_id"]:
                # 获取用户信息对象
                old_assignee_info = await self._get_user_info_dict(old_assignee)
                new_assignee_info = await self._get_user_info_dict(update_data["assignee_id"])

                # 构建action_data，只包含非None的值
                action_data = {}
                if old_assignee_info is not None:
                    action_data["from"] = old_assignee_info
                if new_assignee_info is not None:
                    action_data["to"] = new_assignee_info

                # 只有当有实际变更时才记录timeline
                if action_data:
                    await self._add_timeline(
                        issue_id=issue_id,
                        action_type=TimelineAction.ASSIGNED,
                        user_id=user_id,
                        action_data=action_data,
                    )

        query = (
            update(Issue)
            .where(Issue.id == issue_id, Issue.is_deleted == False)
            .values(**update_data)
        )
        await self.db.execute(query)
        await self.db.commit()

        return await self.get_issue(issue_id)

    async def delete_issue(self, issue_id: str, user_id: str) -> bool:
        """删除 Issue（软删除）"""
        query = (
            update(Issue)
            .where(Issue.id == issue_id)
            .values(
                is_deleted=True,
                updated_by=user_id,
                updated_at=datetime.utcnow(),
            )
        )
        result = await self.db.execute(query)
        await self.db.commit()
        return result.rowcount > 0

    # ========================================================================
    # 批量操作
    # ========================================================================

    async def bulk_update_issues(
        self,
        data: IssueBulkUpdate,
        user_id: str,
    ) -> int:
        """批量更新 Issue"""
        update_data = {
            "updated_by": user_id,
            "updated_at": datetime.utcnow(),
        }

        if data.status is not None:
            update_data["status"] = data.status
        if data.priority is not None:
            update_data["priority"] = data.priority
        if data.assignee_id is not None:
            update_data["assignee_id"] = data.assignee_id

        query = (
            update(Issue)
            .where(
                Issue.id.in_(data.issue_ids),
                Issue.is_deleted == False,
            )
            .values(**update_data)
        )
        result = await self.db.execute(query)
        await self.db.commit()

        return result.rowcount

    async def bulk_delete_issues(
        self,
        issue_ids: List[str],
        user_id: str,
    ) -> int:
        """批量删除 Issue（软删除）"""
        query = (
            update(Issue)
            .where(Issue.id.in_(issue_ids))
            .values(
                is_deleted=True,
                updated_by=user_id,
                updated_at=datetime.utcnow(),
            )
        )
        result = await self.db.execute(query)
        await self.db.commit()

        return result.rowcount

    # ========================================================================
    # 评论操作
    # ========================================================================

    async def add_comment(
        self,
        issue_id: str,
        content: str,
        user_id: str,
        parent_id: Optional[str] = None,
        comment_type: str = "comment",  # 使用小写值，与 CommentType.COMMENT.value 一致
        meta_data: Optional[dict] = None,
    ) -> IssueComment:
        """添加评论"""
        comment = IssueComment(
            issue_id=issue_id,
            user_id=user_id,
            content=content,
            parent_id=parent_id,
            comment_type=comment_type,
            meta_data=meta_data,
        )

        self.db.add(comment)

        # 更新 Issue 评论计数
        await self._increment_comment_count(issue_id)

        # 添加时间线记录
        await self._add_timeline(
            issue_id=issue_id,
            action_type=TimelineAction.COMMENTED,
            user_id=user_id,
            action_data={"comment_id": comment.id, "parent_id": parent_id},
        )

        await self.db.commit()
        # 注释掉 refresh 以避免枚举值问题
        # await self.db.refresh(comment)
        return comment

    async def update_comment(
        self,
        comment_id: str,
        content: str,
        user_id: str,
    ) -> Optional[IssueComment]:
        """更新评论"""
        query = (
            select(IssueComment)
            .where(
                IssueComment.id == comment_id,
                IssueComment.user_id == user_id,
                IssueComment.is_deleted == False,
            )
        )
        result = await self.db.execute(query)
        comment = result.scalar_one_or_none()

        if comment:
            comment.content = content
            comment.updated_at = datetime.utcnow()
            await self.db.commit()
            await self.db.refresh(comment)

        return comment

    async def delete_comment(self, comment_id: str, user_id: str) -> bool:
        """删除评论（软删除）"""
        query = (
            update(IssueComment)
            .where(
                IssueComment.id == comment_id,
                IssueComment.user_id == user_id,
            )
            .values(is_deleted=True, updated_at=datetime.utcnow())
        )
        result = await self.db.execute(query)
        await self.db.commit()

        return result.rowcount > 0

    async def get_comments(
        self,
        issue_id: str,
        include_deleted: bool = False,
    ) -> List[IssueComment]:
        """获取 Issue 的所有评论"""
        query = select(IssueComment).where(IssueComment.issue_id == issue_id)

        if not include_deleted:
            query = query.where(IssueComment.is_deleted == False)

        query = query.order_by(IssueComment.created_at.asc())

        result = await self.db.execute(query)
        return list(result.scalars().all())

    # ========================================================================
    # 关系操作
    # ========================================================================

    async def add_relation(
        self,
        source_id: str,
        target_id: str,
        relation_type: RelationType,
        user_id: str,
    ) -> IssueRelation:
        """添加 Issue 关系"""
        relation = IssueRelation(
            source_id=source_id,
            target_id=target_id,
            relation_type=relation_type,
            created_by=user_id,
        )

        self.db.add(relation)

        # 添加时间线记录
        await self._add_timeline(
            issue_id=source_id,
            action_type=TimelineAction.RELATION_ADDED,
            user_id=user_id,
            action_data={
                "target_id": target_id,
                "relation_type": relation_type.value,
            },
        )

        await self.db.commit()
        await self.db.refresh(relation)
        return relation

    async def remove_relation(
        self,
        source_id: str,
        target_id: str,
        relation_type: RelationType,
    ) -> bool:
        """移除 Issue 关系"""
        query = delete(IssueRelation).where(
            and_(
                IssueRelation.source_id == source_id,
                IssueRelation.target_id == target_id,
                IssueRelation.relation_type == relation_type,
            )
        )
        result = await self.db.execute(query)
        await self.db.commit()

        return result.rowcount > 0

    async def get_relations(
        self,
        issue_id: str,
    ) -> Tuple[List[IssueRelation], List[IssueRelation]]:
        """获取 Issue 的所有关系"""
        # 作为源的关系
        source_query = select(IssueRelation).where(
            IssueRelation.source_id == issue_id
        )
        source_result = await self.db.execute(source_query)
        source_relations = list(source_result.scalars().all())

        # 作为目标的关系
        target_query = select(IssueRelation).where(
            IssueRelation.target_id == issue_id
        )
        target_result = await self.db.execute(target_query)
        target_relations = list(target_result.scalars().all())

        return source_relations, target_relations

    # ========================================================================
    # 标签操作
    # ========================================================================

    async def add_tag(
        self,
        issue_id: str,
        tag_id: int,
        user_id: Optional[str] = None,
    ) -> IssueTag:
        """添加标签到 Issue"""
        issue_tag = IssueTag(issue_id=issue_id, tag_id=tag_id)
        self.db.add(issue_tag)

        # 添加时间线记录
        await self._add_timeline(
            issue_id=issue_id,
            user_id=user_id,
            action_type=TimelineAction.LABEL_ADDED,
            action_data={"tag_id": tag_id},
        )

        await self.db.commit()
        await self.db.refresh(issue_tag)
        return issue_tag

    async def remove_tag(
        self,
        issue_id: str,
        tag_id: int,
    ) -> bool:
        """从 Issue 移除标签"""
        query = delete(IssueTag).where(
            and_(
                IssueTag.issue_id == issue_id,
                IssueTag.tag_id == tag_id,
            )
        )
        result = await self.db.execute(query)
        await self.db.commit()

        return result.rowcount > 0

    async def get_tags(self, issue_id: str) -> List[IssueTag]:
        """获取 Issue 的所有标签"""
        # Tag 功能已移除，返回空列表
        return []

    # ========================================================================
    # 反应操作
    # ========================================================================

    async def get_reactions(self, issue_id: str) -> List[IssueReaction]:
        """获取 Issue 的所有反应"""
        result = await self.db.execute(
            select(IssueReaction)
            .where(IssueReaction.issue_id == issue_id)
            .order_by(IssueReaction.created_at.desc())
        )
        return list(result.scalars().all())

    async def add_reaction(
        self,
        issue_id: str,
        emoji: str,
        user_id: str,
    ) -> IssueReaction:
        """添加反应（幂等操作：如果反应已存在则直接返回）"""
        # 检查是否已经存在该反应
        result = await self.db.execute(
            select(IssueReaction)
            .where(
                and_(
                    IssueReaction.issue_id == issue_id,
                    IssueReaction.emoji == emoji,
                    IssueReaction.user_id == user_id
                )
            )
        )
        existing_reaction = result.scalar_one_or_none()

        # 如果反应已存在，直接返回
        if existing_reaction:
            return existing_reaction

        # 创建新反应
        reaction = IssueReaction(
            issue_id=issue_id,
            emoji=emoji,
            user_id=user_id
        )
        self.db.add(reaction)
        await self.db.commit()
        await self.db.refresh(reaction)

        # 记录到时间线
        await self._add_timeline(
            issue_id=issue_id,
            user_id=user_id,
            action_type=TimelineAction.REACTION_ADDED,
            action_data={"emoji": emoji}
        )

        return reaction

    async def remove_reaction(
        self,
        issue_id: str,
        emoji: str,
        user_id: str,
    ) -> bool:
        """移除反应"""
        result = await self.db.execute(
            delete(IssueReaction)
            .where(
                and_(
                    IssueReaction.issue_id == issue_id,
                    IssueReaction.emoji == emoji,
                    IssueReaction.user_id == user_id
                )
            )
        )
        await self.db.commit()
        deleted = result.rowcount > 0

        if deleted:
            # 记录到时间线
            await self._add_timeline(
                issue_id=issue_id,
                user_id=user_id,
                action_type=TimelineAction.REACTION_REMOVED,
                action_data={"emoji": emoji}
            )

        return deleted

    async def get_reaction_stats(self, issue_id: str) -> Dict[str, Any]:
        """获取反应统计（按 emoji 分组）"""
        reactions = await self.get_reactions(issue_id)

        stats = {}
        for reaction in reactions:
            if reaction.emoji not in stats:
                stats[reaction.emoji] = {
                    "emoji": reaction.emoji,
                    "count": 0,
                    "users": []
                }
            stats[reaction.emoji]["count"] += 1
            stats[reaction.emoji]["users"].append(reaction.user_id)

        return stats

    # ========================================================================
    # 时间线操作
    # ========================================================================

    async def get_timeline(
        self,
        issue_id: str,
        limit: int = 50,
    ) -> List[IssueTimeline]:
        """获取 Issue 时间线"""
        query = (
            select(IssueTimeline)
            .where(IssueTimeline.issue_id == issue_id)
            .order_by(IssueTimeline.created_at.desc())
            .limit(limit)
        )
        result = await self.db.execute(query)
        timelines = list(result.scalars().all())

        # 转换旧格式的用户 ID 为用户对象（向后兼容）
        for timeline in timelines:
            if timeline.action_data and timeline.action_type == TimelineAction.ASSIGNED:
                # 转换 from 字段
                if timeline.action_data.get("from"):
                    from_value = timeline.action_data["from"]
                    if isinstance(from_value, str):
                        # 旧格式：字符串 ID，转换为用户对象
                        timeline.action_data["from"] = await self._get_user_info_dict(from_value)

                # 转换 to 字段
                if timeline.action_data.get("to"):
                    to_value = timeline.action_data["to"]
                    if isinstance(to_value, str):
                        # 旧格式：字符串 ID，转换为用户对象
                        timeline.action_data["to"] = await self._get_user_info_dict(to_value)

        return timelines

    # ========================================================================
    # 统计操作
    # ========================================================================

    async def get_statistics(
        self,
        project_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """获取 Issue 统计信息"""
        query = select(Issue).where(Issue.is_deleted == False)

        if project_id:
            query = query.where(Issue.project_id == project_id)

        # 总数
        total_result = await self.db.execute(
            select(func.count()).select_from(query.subquery())
        )
        total = total_result.scalar()

        # 按状态统计
        status_query = select(Issue.status, func.count()).where(
            Issue.is_deleted == False
        )
        if project_id:
            status_query = status_query.where(Issue.project_id == project_id)
        status_query = status_query.group_by(Issue.status)
        status_result = await self.db.execute(status_query)
        by_status = {getattr(status, "value", status): count for status, count in status_result.all()}

        # 按优先级统计
        priority_query = select(Issue.priority, func.count()).where(
            Issue.is_deleted == False
        )
        if project_id:
            priority_query = priority_query.where(Issue.project_id == project_id)
        priority_query = priority_query.group_by(Issue.priority)
        priority_result = await self.db.execute(priority_query)
        by_priority = {getattr(priority, "value", priority): count for priority, count in priority_result.all()}

        # 按类型统计
        type_query = select(Issue.type, func.count()).where(
            Issue.is_deleted == False
        )
        if project_id:
            type_query = type_query.where(Issue.project_id == project_id)
        type_query = type_query.group_by(Issue.type)
        type_result = await self.db.execute(type_query)
        by_type = {getattr(type_, "value", type_): count for type_, count in type_result.all()}

        # 各状态计数
        open_count = by_status.get(IssueStatus.OPEN.value, 0)
        in_progress_count = by_status.get(IssueStatus.IN_PROGRESS.value, 0)
        resolved_count = by_status.get(IssueStatus.RESOLVED.value, 0)
        closed_count = by_status.get(IssueStatus.CLOSED.value, 0)

        return {
            "total": total,
            "by_status": by_status,
            "by_priority": by_priority,
            "by_type": by_type,
            "open_count": open_count,
            "in_progress_count": in_progress_count,
            "resolved_count": resolved_count,
            "closed_count": closed_count,
        }

    # ========================================================================
    # 私有辅助方法
    # ========================================================================

    async def _add_timeline(
        self,
        issue_id: str,
        action_type: TimelineAction,
        user_id: Optional[str],
        action_data: Optional[dict] = None,
    ) -> IssueTimeline:
        """添加时间线记录"""
        timeline = IssueTimeline(
            issue_id=issue_id,
            user_id=user_id,
            action_type=action_type,
            action_data=action_data,
        )
        self.db.add(timeline)
        return timeline

    async def _increment_comment_count(self, issue_id: str):
        """增加评论计数"""
        query = (
            update(Issue)
            .where(Issue.id == issue_id)
            .values(comment_count=Issue.comment_count + 1)
        )
        await self.db.execute(query)

    async def _get_issue_status(self, issue_id: str) -> Optional[str]:
        """获取 Issue 状态"""
        query = select(Issue.status).where(Issue.id == issue_id)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def _get_issue_priority(self, issue_id: str) -> Optional[str]:
        """获取 Issue 优先级"""
        query = select(Issue.priority).where(Issue.id == issue_id)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def _get_issue_assignee(self, issue_id: str) -> Optional[str]:
        """获取 Issue 负责人"""
        query = select(Issue.assignee_id).where(Issue.id == issue_id)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def _get_user_info_dict(self, user_id: Optional[str]) -> Optional[dict]:
        """获取用户信息的字典格式"""
        if not user_id:
            return None

        from opentask.models.user.model import UserModel

        try:
            # 直接使用 SQLAlchemy 查询用户
            query = select(UserModel).where(UserModel.id == user_id)
            result = await self.db.execute(query)
            user = result.scalar_one_or_none()

            if not user:
                return None

            return {
                "id": str(user.id),  # 将 UUID 转换为字符串
                "sso_name": user.sso_name,
                "sso_account": user.sso_account,
                "name": user.name
            }
        except Exception:
            # 如果用户不存在，返回 None
            return None

    # ========================================================================
    # 附件操作
    # ========================================================================

    async def get_attachments(self, issue_id: str) -> List[Document]:
        """获取 Issue 的所有附件"""
        query = select(Document).where(
            and_(
                Document.entity_type == "issue",
                Document.entity_id == issue_id
            )
        ).order_by(Document.created_at.desc())

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_attachment(self, issue_id: str, attachment_id: str) -> Optional[Document]:
        """获取单个附件"""
        query = select(Document).where(
            and_(
                Document.id == attachment_id,
                Document.entity_type == "issue",
                Document.entity_id == issue_id
            )
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_attachment_by_id(self, attachment_id: str) -> Optional[Document]:
        """通过附件 ID 直接获取附件（用于公共下载接口）"""
        query = select(Document).where(
            and_(
                Document.id == attachment_id,
                Document.entity_type == "issue"
            )
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def add_attachment(
        self,
        issue_id: str,
        file_path: str,
        file_name: str,
        file_type: str,
        file_size: int,
        user_id: str,
        dept_id: str | None = None,
    ) -> Document:
        """添加附件到 Issue

        dept_id: 上传人主部门 id 快照（None 表示无归属，行保持 NULL）
        """
        # 验证 Issue 是否存在
        issue = await self.db.execute(
            select(Issue).where(Issue.id == issue_id)
        )
        if not issue.scalar_one_or_none():
            raise ValueError(f"Issue {issue_id} 不存在")

        # 创建附件记录
        attachment = Document(
            entity_type="issue",
            entity_id=issue_id,
            file_path=file_path,
            file_name=file_name,
            file_type=file_type,
            file_size=file_size,
            created_by=user_id,
            updated_by=user_id,
            dept_id=dept_id,  # 部门归属快照
        )

        self.db.add(attachment)

        # 更新 Issue 附件计数
        await self._increment_attachment_count(issue_id)

        # 添加时间线记录
        await self._add_timeline(
            issue_id=issue_id,
            action_type=TimelineAction.ATTACHMENT_ADDED,
            user_id=user_id,
            action_data={
                "file_name": file_name,
                "file_type": file_type,
                "file_size": file_size,
            },
        )

        await self.db.commit()
        await self.db.refresh(attachment)
        return attachment

    async def delete_attachment(self, issue_id: str, attachment_id: str, user_id: str) -> bool:
        """删除 Issue 附件"""
        # 获取附件信息
        attachment = await self.get_attachment(issue_id, attachment_id)
        if not attachment:
            return False

        # 删除物理文件
        storage_service = get_storage_service()
        storage_service.delete_file(attachment.file_path)

        # 删除数据库记录
        query = delete(Document).where(Document.id == attachment_id)
        result = await self.db.execute(query)

        # 更新 Issue 附件计数
        await self._decrement_attachment_count(issue_id)

        # 添加时间线记录
        await self._add_timeline(
            issue_id=issue_id,
            action_type=TimelineAction.ATTACHMENT_REMOVED,
            user_id=user_id,
            action_data={
                "file_name": attachment.file_name,
            },
        )

        await self.db.commit()
        return result.rowcount > 0

    async def _increment_attachment_count(self, issue_id: str):
        """增加附件计数"""
        query = (
            update(Issue)
            .where(Issue.id == issue_id)
            .values(attachment_count=Issue.attachment_count + 1)
        )
        await self.db.execute(query)

    async def _decrement_attachment_count(self, issue_id: str):
        """减少附件计数"""
        query = (
            update(Issue)
            .where(Issue.id == issue_id)
            .values(attachment_count=Issue.attachment_count - 1)
        )
        await self.db.execute(query)
