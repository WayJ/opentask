"""Issue 服务层"""
from typing import Optional, List, Tuple, Dict, Any
from datetime import datetime, date, timedelta
import re
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, update, delete, or_, and_
from sqlalchemy.orm import selectinload, joinedload

from opentask.services.custom_field.service import FORMULA_SORT_CANDIDATE_CAP

_CF_SORT_RE = re.compile(r"^cf:([a-z][a-z0-9_-]{0,63})$")
_CF_SORT_OK_TYPES = frozenset({"number", "text", "date", "boolean"})

from opentask.models.issue.model import (
    Issue,
    IssueComment,
    IssueRelation,
    IssueTimeline,
    IssueTag,
    IssueReaction,
    CommentReaction,
)
from opentask.models.document.model import Document
from opentask.services.storage.service import get_storage_service
from opentask.models.issue.schema import (
    IssueCreate,
    IssueUpdate,
    IssueBulkUpdate,
    IssueBoardMove,
    IssueQueryParams,
)
from opentask.models.issue.enums import (
    IssueStatus,
    IssuePriority,
    TimelineAction,
    RelationType,
)
from opentask.models.cycle.model import Cycle
from opentask.models.milestone.model import Milestone
from opentask.services.user_center.rbac_service import RbacService
from opentask.services.notification.service import NotificationService
from opentask.services.automation.service import fire_automations
from opentask.services.workspace_webhook.service import fire_webhooks
from opentask.services.sla.service import SlaService
from opentask.services.workspace_realtime import (
    publish_comment_created,
    publish_issue_created,
    publish_issue_deleted,
    publish_issue_updated,
)

from opentask.models.workspace.model import Workspace


class IssueService:
    """Issue 服务"""

    @staticmethod
    def _naive_utc(value):
        """TIMESTAMP WITHOUT TIME ZONE：去掉 tzinfo（按 UTC 墙钟）。"""
        if value is None:
            return None
        if isinstance(value, datetime) and value.tzinfo is not None:
            return value.replace(tzinfo=None)
        return value


    def __init__(self, db: AsyncSession):
        self.db = db

    async def _generate_issue_code(self, workspace_id: str | None = None) -> str:
        """生成问题编号。

        有 workspace_id：KEY-N（工作区 issue_key + 行级 counter 递增）。
        无 workspace_id：保留历史 ISSUE{year}-N（孤儿/无头路径）。
        """
        from datetime import datetime
        from sqlalchemy import text

        if workspace_id:
            result = await self.db.execute(
                select(Workspace)
                .where(Workspace.id == workspace_id)
                .with_for_update()
            )
            ws = result.scalar_one_or_none()
            if ws is None:
                raise ValueError(f"工作区不存在: {workspace_id}")
            ws.issue_counter = int(ws.issue_counter or 0) + 1
            await self.db.flush()
            return f"{ws.issue_key}-{ws.issue_counter}"

        current_year = datetime.now().year
        prefix = f"ISSUE{current_year}-"
        query = text(
            "SELECT issue_code FROM issues "
            "WHERE issue_code LIKE :prefix_pattern"
        )
        result = await self.db.execute(query, {"prefix_pattern": f"{prefix}%"})
        max_num = 0
        for (code,) in result:
            suffix = code[len(prefix):]
            try:
                num = int(suffix)
            except (TypeError, ValueError):
                continue
            max_num = max(max_num, num)
        return f"{prefix}{max_num + 1}"

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
        custom_field_filters: list[tuple[str, str, str]] | None = None,
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
        if params.cycle_id:
            if params.cycle_id == "__none__":
                query = query.where(Issue.cycle_id.is_(None))
            else:
                query = query.where(Issue.cycle_id == params.cycle_id)
        if getattr(params, "milestone_id", None):
            if params.milestone_id == "__none__":
                query = query.where(Issue.milestone_id.is_(None))
            else:
                query = query.where(Issue.milestone_id == params.milestone_id)
        if params.search:
            search_pattern = f"%{params.search}%"
            query = query.where(
                or_(
                    Issue.title.ilike(search_pattern),
                    Issue.description.ilike(search_pattern),
                    Issue.issue_code.ilike(search_pattern),
                    Issue.legacy_issue_code.ilike(search_pattern),
                )
            )

        # E19：watching / due_before / due_soon
        if getattr(params, "watching", None) and user_id:
            from opentask.models.issue_watcher.model import IssueWatcher

            query = query.join(
                IssueWatcher,
                and_(
                    IssueWatcher.issue_id == Issue.id,
                    IssueWatcher.user_id == str(user_id),
                ),
            )
        if getattr(params, "due_before", None):
            try:
                before = date.fromisoformat(str(params.due_before)[:10])
            except ValueError:
                before = None
            if before is not None:
                query = query.where(
                    Issue.due_date.is_not(None),
                    func.date(Issue.due_date) <= before,
                )
        if getattr(params, "due_soon", None):
            today = date.today()
            until = today + timedelta(days=3)
            closed = {
                IssueStatus.CLOSED.value,
                IssueStatus.RESOLVED.value,
                IssueStatus.REJECTED.value,
            }
            query = query.where(
                Issue.due_date.is_not(None),
                func.date(Issue.due_date) >= today,
                func.date(Issue.due_date) <= until,
                Issue.status.notin_(list(closed)),
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

        # E32：自定义字段过滤（须属当前 workspace）
        if custom_field_filters and workspace_id is not None:
            from opentask.services.custom_field.service import CustomFieldService

            query = await CustomFieldService(self.db).apply_list_filters(
                query, workspace_id=workspace_id, filters=custom_field_filters
            )
        elif custom_field_filters:
            # 无 WS 上下文时忽略 cf 过滤（避免跨租户误匹配）
            query = query.where(Issue.id.in_([]))

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
        total = result.scalar() or 0

        # E46：sort_by=cf:<key> — 内存排序（cap + nulls last）
        cf_sort_m = _CF_SORT_RE.match((params.sort_by or "").strip())
        if cf_sort_m:
            return await self._list_sorted_by_cf(
                query=query,
                total=total,
                workspace_id=workspace_id,
                field_key=cf_sort_m.group(1),
                sort_order=(params.sort_order or "desc").lower(),
                page=params.page,
                page_size=params.page_size,
            )

        # 排序（白名单；position 支持看板同源排序，NULL 靠后）
        allowed_sort = {
            "created_at",
            "updated_at",
            "position",
            "priority",
            "status",
            "title",
            "due_date",
        }
        sort_key = params.sort_by if params.sort_by in allowed_sort else "created_at"
        sort_column = getattr(Issue, sort_key)
        if sort_key == "position":
            if params.sort_order == "asc":
                query = query.order_by(sort_column.asc().nulls_last(), Issue.created_at.asc())
            else:
                query = query.order_by(sort_column.desc().nulls_last(), Issue.created_at.desc())
        elif params.sort_order == "asc":
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

    async def _list_sorted_by_cf(
        self,
        *,
        query,
        total: int,
        workspace_id: str | None,
        field_key: str,
        sort_order: str,
        page: int,
        page_size: int,
    ) -> Tuple[List[Issue], int]:
        from opentask.services.custom_field.service import CustomFieldService

        if workspace_id is None:
            raise HTTPException(
                status_code=400,
                detail={
                    "code": "cf_sort_unsupported",
                    "message": "cf 排序需要工作区上下文",
                },
            )
        cf_svc = CustomFieldService(self.db)
        field = await cf_svc.get_by_key_optional(
            workspace_id=workspace_id, key=field_key
        )
        if field is None or field.archived_at is not None:
            raise HTTPException(
                status_code=400,
                detail={
                    "code": "cf_sort_unsupported",
                    "message": f"字段 {field_key} 不存在或已归档",
                },
            )
        result_type = field.type
        if field.type == "formula":
            result_type = (
                getattr(field, "formula_result_type", None) or "number"
            ).strip() or "number"
        if field.type == "multi_select" or result_type not in _CF_SORT_OK_TYPES:
            raise HTTPException(
                status_code=400,
                detail={
                    "code": "cf_sort_unsupported",
                    "message": f"字段 {field_key} 类型不支持排序",
                },
            )
        if total > FORMULA_SORT_CANDIDATE_CAP:
            raise HTTPException(
                status_code=400,
                detail={
                    "code": "formula_sort_too_broad",
                    "message": (
                        f"公式/CF 排序候选超过 {FORMULA_SORT_CANDIDATE_CAP}，"
                        "请先用过滤条件收窄"
                    ),
                },
            )

        id_rows = await self.db.execute(
            query.order_by(None).with_only_columns(Issue.id).distinct()
        )
        candidate_ids = [row[0] for row in id_rows.all()]
        if not candidate_ids:
            return [], total

        # load issues with same options as list
        iss_q = (
            select(Issue)
            .options(
                joinedload(Issue.assignee),
                joinedload(Issue.reporter),
            )
            .where(Issue.id.in_(candidate_ids))
        )
        iss_res = await self.db.execute(iss_q)
        issues = list(iss_res.scalars().unique().all())
        by_id = {i.id: i for i in issues}

        bundled = await cf_svc.values_for_issues(
            workspace_id=workspace_id, issue_ids=candidate_ids
        )

        def _entry_val(iid: str):
            items = bundled.get(iid) or []
            entry = next((x for x in items if x.get("key") == field_key), None)
            if not entry or entry.get("error"):
                return None
            return entry.get("value")

        def _primary(iid: str):
            """Return (null_rank, primary) — null_rank 1 sorts last."""
            val = _entry_val(iid)
            if val is None:
                return 1, None
            if result_type == "number":
                try:
                    return 0, float(val)
                except (TypeError, ValueError):
                    return 1, None
            if result_type == "boolean":
                return 0, 1 if val else 0
            return 0, str(val)

        reverse = sort_order == "desc"

        def _sort_key(iid: str):
            null_rank, primary = _primary(iid)
            issue = by_id[iid]
            created = issue.created_at or datetime.min
            if null_rank == 1:
                # nulls last: high null_rank; within nulls use created/id
                return (1, created if not reverse else datetime.max - (created - datetime.min) if False else created, iid)
            # non-null: decorate primary for reverse via sign flip for numbers, else leave and reverse list
            return (0, primary, created, iid)

        non_null = [i for i in candidate_ids if _primary(i)[0] == 0]
        nulls = [i for i in candidate_ids if _primary(i)[0] == 1]
        non_null.sort(
            key=lambda i: (_primary(i)[1], by_id[i].created_at or datetime.min, i),
            reverse=reverse,
        )
        nulls.sort(
            key=lambda i: (by_id[i].created_at or datetime.min, i),
            reverse=reverse,
        )
        ordered_ids = non_null + nulls
        offset = (page - 1) * page_size
        page_ids = ordered_ids[offset : offset + page_size]
        return [by_id[i] for i in page_ids if i in by_id], total

    async def get_issue(
        self,
        issue_id: str,
        by_code: bool = False,
        workspace_id: str | None = None,
    ) -> Optional[Issue]:
        """获取单个 Issue。

        by_code: 按 issue_code 或 legacy_issue_code 查询。
        workspace_id: 若提供则限制租户（跨 WS by_code → 找不到）。
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

        if by_code:
            query = query.where(
                or_(
                    Issue.issue_code == issue_id,
                    Issue.legacy_issue_code == issue_id,
                )
            )
            if workspace_id is not None:
                query = query.where(Issue.workspace_id == workspace_id)
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


    async def list_child_issues(self, parent_id: str) -> List[Issue]:
        """列出未删除的直接子 Issue（depth-1）。"""
        query = (
            select(Issue)
            .where(
                Issue.parent_issue_id == parent_id,
                Issue.is_deleted == False,
            )
            .order_by(Issue.created_at.asc())
        )
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def _validate_parent_issue_id(
        self,
        *,
        issue_id: str | None,
        parent_issue_id: str | None,
        workspace_id: str | None,
    ) -> None:
        """校验父 Issue：存在、同工作区、非自指、不成环。"""
        if parent_issue_id is None:
            return
        if issue_id is not None and parent_issue_id == issue_id:
            raise ValueError("不能将自身设为父 Issue")

        parent = await self.get_issue(parent_issue_id)
        if not parent:
            raise ValueError("父 Issue 不存在")

        if workspace_id is not None and parent.workspace_id != workspace_id:
            raise ValueError("父 Issue 必须属于同一工作区")
        if workspace_id is None and parent.workspace_id is not None:
            raise ValueError("父 Issue 必须属于同一工作区")

        # 环检测：从拟设父节点沿祖先上行，不可碰到 issue_id
        if issue_id is not None:
            cursor = parent
            seen: set[str] = set()
            while cursor is not None:
                if cursor.id == issue_id:
                    raise ValueError("不能形成父子循环")
                if cursor.id in seen:
                    break
                seen.add(cursor.id)
                if not cursor.parent_issue_id:
                    break
                cursor = await self.get_issue(cursor.parent_issue_id)


    async def _validate_cycle_id(
        self,
        *,
        cycle_id: str | None,
        workspace_id: str | None,
    ) -> None:
        """校验 Cycle：存在且属于同一工作区。"""
        if cycle_id is None:
            return
        result = await self.db.execute(select(Cycle).where(Cycle.id == cycle_id))
        cycle = result.scalar_one_or_none()
        if not cycle:
            raise ValueError("Cycle 不存在")
        if workspace_id is None or cycle.workspace_id != workspace_id:
            raise ValueError("Cycle 必须属于同一工作区")

    async def _validate_milestone_id(
        self,
        *,
        milestone_id: str | None,
        issue_project_id: str | None,
        workspace_id: str | None,
    ) -> None:
        """校验 Milestone：存在、同工作区，且 milestone.project_id == issue.project_id。"""
        if milestone_id is None:
            return
        if not issue_project_id:
            raise ValueError("Issue 未关联项目，不能挂载里程碑")
        result = await self.db.execute(select(Milestone).where(Milestone.id == milestone_id))
        ms = result.scalar_one_or_none()
        if not ms:
            raise ValueError("里程碑不存在")
        if workspace_id is None or ms.workspace_id != workspace_id:
            raise ValueError("里程碑必须属于同一工作区")
        if ms.project_id != issue_project_id:
            raise ValueError("里程碑必须属于 Issue 所在项目")

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
        issue_code = await self._generate_issue_code(workspace_id)

        issue_data = data.model_dump()
        issue_data.pop("template_id", None)
        if "due_date" in issue_data:
            issue_data["due_date"] = self._naive_utc(issue_data.get("due_date"))
        await self._validate_parent_issue_id(
            issue_id=None,
            parent_issue_id=issue_data.get("parent_issue_id"),
            workspace_id=workspace_id,
        )
        await self._validate_cycle_id(
            cycle_id=issue_data.get("cycle_id"),
            workspace_id=workspace_id,
        )
        await self._validate_milestone_id(
            milestone_id=issue_data.get("milestone_id"),
            issue_project_id=issue_data.get("project_id"),
            workspace_id=workspace_id,
        )
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
            action_data={"title": issue.title, "type": (issue.type.value if hasattr(issue.type, "value") else issue.type), "issue_code": issue_code},
        )

        # E42：create 时若 status∈start 也启钟（同事务）
        await SlaService(self.db).sync_clocks(
            issue=issue,
            old_status=None,
            new_status=getattr(issue.status, "value", issue.status),
        )

        await self.db.commit()
        await self.db.refresh(issue)
        await publish_issue_created(issue, actor_user_id=user_id)
        await fire_automations(
            self.db,
            workspace_id=issue.workspace_id,
            trigger_type="issue.created",
            issue=issue,
            actor_user_id=user_id,
        )
        await fire_webhooks(
            self.db,
            workspace_id=issue.workspace_id,
            event_type="issue.created",
            data={
                "id": str(issue.id),
                "issueCode": issue.issue_code,
                "title": issue.title,
                "status": getattr(issue.status, "value", issue.status),
                "priority": getattr(issue.priority, "value", issue.priority),
            },
        )
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

        if "parent_issue_id" in update_data:
            existing = await self.get_issue(issue_id)
            if not existing:
                return None
            await self._validate_parent_issue_id(
                issue_id=issue_id,
                parent_issue_id=update_data.get("parent_issue_id"),
                workspace_id=existing.workspace_id,
            )

        if "cycle_id" in update_data:
            existing = await self.get_issue(issue_id)
            if not existing:
                return None
            await self._validate_cycle_id(
                cycle_id=update_data.get("cycle_id"),
                workspace_id=existing.workspace_id,
            )

        if "milestone_id" in update_data:
            existing = await self.get_issue(issue_id)
            if not existing:
                return None
            # project_id may also be updating in same payload
            project_id = update_data.get("project_id", existing.project_id)
            await self._validate_milestone_id(
                milestone_id=update_data.get("milestone_id"),
                issue_project_id=project_id,
                workspace_id=existing.workspace_id,
            )

        update_data["updated_by"] = user_id

        # 记录状态变更
        status_changed = None  # (old, new)
        if "status" in update_data:
            old_status = await self._get_issue_status(issue_id)
            if old_status != update_data["status"]:
                status_changed = (old_status, update_data["status"])
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

        # E19：截止日期变更
        due_date_changed = None  # (old, new)
        if "due_date" in update_data:
            update_data["due_date"] = self._naive_utc(update_data.get("due_date"))
            old_due_q = await self.db.execute(
                select(Issue.due_date).where(Issue.id == issue_id)
            )
            old_due = old_due_q.scalar_one_or_none()
            new_due = update_data.get("due_date")
            # normalize for compare
            def _due_key(v):
                if v is None:
                    return None
                if isinstance(v, datetime):
                    return v.replace(tzinfo=None).isoformat()
                return str(v)

            if _due_key(old_due) != _due_key(new_due):
                due_date_changed = (old_due, new_due)
                await self._add_timeline(
                    issue_id=issue_id,
                    action_type=TimelineAction.DUE_DATE_CHANGED,
                    user_id=user_id,
                    action_data={
                        "from": old_due.isoformat() if isinstance(old_due, datetime) else old_due,
                        "to": new_due.isoformat() if isinstance(new_due, datetime) else new_due,
                    },
                )

        # 记录分配变更
        assignee_changed_to = None
        assignee_changed_from = None
        assignee_did_change = False
        if "assignee_id" in update_data:
            old_assignee = await self._get_issue_assignee(issue_id)
            if old_assignee != update_data["assignee_id"]:
                assignee_changed_from = old_assignee
                assignee_changed_to = update_data["assignee_id"]
                assignee_did_change = True
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

        # E41：cycle / estimate / project 变更 → timeline（同事务）
        # E51：捕获实际变更供专用 webhook（与 issue.updated 并存）
        cycle_changed_pair = None  # (from, to)
        estimate_changed_pair = None
        project_changed_pair = None
        if "cycle_id" in update_data:
            old_cycle_q = await self.db.execute(
                select(Issue.cycle_id).where(Issue.id == issue_id)
            )
            old_cycle = old_cycle_q.scalar_one_or_none()
            new_cycle = update_data.get("cycle_id")
            if old_cycle != new_cycle:
                cycle_changed_pair = (old_cycle, new_cycle)
                await self._add_timeline(
                    issue_id=issue_id,
                    action_type=TimelineAction.CYCLE_CHANGED,
                    user_id=user_id,
                    action_data={"from": old_cycle, "to": new_cycle},
                )

        if "estimate_points" in update_data:
            old_est_q = await self.db.execute(
                select(Issue.estimate_points).where(Issue.id == issue_id)
            )
            old_est = old_est_q.scalar_one_or_none()
            new_est = update_data.get("estimate_points")

            def _est_num(v):
                if v is None:
                    return None
                try:
                    return float(v)
                except (TypeError, ValueError):
                    return v

            old_n, new_n = _est_num(old_est), _est_num(new_est)
            if old_n != new_n:
                estimate_changed_pair = (old_n, new_n)
                await self._add_timeline(
                    issue_id=issue_id,
                    action_type=TimelineAction.ESTIMATE_CHANGED,
                    user_id=user_id,
                    action_data={"from": old_n, "to": new_n},
                )

        if "project_id" in update_data:
            old_proj_q = await self.db.execute(
                select(Issue.project_id).where(Issue.id == issue_id)
            )
            old_proj = old_proj_q.scalar_one_or_none()
            new_proj = update_data.get("project_id")
            if old_proj != new_proj:
                project_changed_pair = (old_proj, new_proj)
                await self._add_timeline(
                    issue_id=issue_id,
                    action_type=TimelineAction.PROJECT_CHANGED,
                    user_id=user_id,
                    action_data={"from": old_proj, "to": new_proj},
                )

        query = (
            update(Issue)
            .where(Issue.id == issue_id, Issue.is_deleted == False)
            .values(**update_data)
        )
        await self.db.execute(query)

        # E42：status 实际变更 → 同事务启停 SLA 时钟
        if status_changed:
            old_s, new_s = status_changed
            issue_for_sla = await self.get_issue(issue_id)
            if issue_for_sla:
                await SlaService(self.db).sync_clocks(
                    issue=issue_for_sla,
                    old_status=str(getattr(old_s, "value", old_s)) if old_s is not None else None,
                    new_status=str(getattr(new_s, "value", new_s)),
                )

        await self.db.commit()

        issue = await self.get_issue(issue_id)
        if issue and assignee_changed_to:
            await NotificationService(self.db).notify_assigned(
                issue,
                actor_user_id=user_id,
                new_assignee_id=assignee_changed_to,
            )
        if issue and status_changed:
            old_s, new_s = status_changed
            new_s_val = getattr(new_s, "value", new_s)
            old_s_val = getattr(old_s, "value", old_s) if old_s is not None else None
            await NotificationService(self.db).notify_status_changed(
                issue,
                actor_user_id=user_id,
                old_status=str(old_s_val) if old_s_val is not None else None,
                new_status=str(new_s_val),
            )
        if issue and due_date_changed:
            old_d, new_d = due_date_changed
            await NotificationService(self.db).notify_due_date_changed(
                issue,
                actor_user_id=user_id,
                old_due=old_d,
                new_due=new_d,
            )
        # E43: best-effort formula cache refresh when issue attrs used by formulas change
        if issue and issue.workspace_id:
            formula_attrs: list[str] = []
            if status_changed:
                formula_attrs.append("status")
            if "priority" in update_data:
                formula_attrs.append("priority")
            if due_date_changed:
                formula_attrs.extend(["due_date", "days_until_due"])
            if "estimate_points" in update_data:
                formula_attrs.append("estimate_points")
            if formula_attrs:
                try:
                    from opentask.services.custom_field.service import CustomFieldService

                    await CustomFieldService(self.db).refresh_formula_cache_for_issue(
                        workspace_id=issue.workspace_id,
                        issue_id=issue_id,
                        depending_on_issue_attrs=formula_attrs,
                    )
                except Exception:
                    import logging

                    logging.getLogger(__name__).exception(
                        "formula cache refresh on issue update failed issue=%s", issue_id
                    )
        if issue:
            # exclude internal bookkeeping keys from changed summary
            changed = [
                k
                for k in update_data.keys()
                if k not in {"updated_by", "updated_at"}
            ]
            await publish_issue_updated(
                issue, actor_user_id=user_id, changed=changed
            )
            await fire_webhooks(
                self.db,
                workspace_id=issue.workspace_id,
                event_type="issue.updated",
                data={
                    "id": str(issue.id),
                    "issueCode": issue.issue_code,
                    "title": issue.title,
                    "status": getattr(issue.status, "value", issue.status),
                    "changed": changed,
                },
            )
            if status_changed:
                old_s, new_s = status_changed
                await fire_automations(
                    self.db,
                    workspace_id=issue.workspace_id,
                    trigger_type="issue.status_changed",
                    issue=issue,
                    actor_user_id=user_id,
                    event={
                        "from": str(getattr(old_s, "value", old_s)) if old_s is not None else None,
                        "to": str(getattr(new_s, "value", new_s)),
                    },
                )
                await fire_webhooks(
                    self.db,
                    workspace_id=issue.workspace_id,
                    event_type="issue.status_changed",
                    data={
                        "id": str(issue.id),
                        "issueCode": issue.issue_code,
                        "from": str(getattr(old_s, "value", old_s)) if old_s is not None else None,
                        "to": str(getattr(new_s, "value", new_s)),
                    },
                )
            if assignee_did_change:
                await fire_automations(
                    self.db,
                    workspace_id=issue.workspace_id,
                    trigger_type="issue.assignee_changed",
                    issue=issue,
                    actor_user_id=user_id,
                    event={"to": assignee_changed_to},
                )
                # E44: dedicated outbound webhook (also keep issue.updated above)
                await fire_webhooks(
                    self.db,
                    workspace_id=issue.workspace_id,
                    event_type="issue.assignee_changed",
                    data={
                        "id": str(issue.id),
                        "issueCode": issue.issue_code,
                        "title": issue.title,
                        "from": assignee_changed_from,
                        "to": assignee_changed_to,
                        "actorUserId": user_id,
                    },
                )
            # E51: dedicated cycle/estimate/project webhooks (coexist with issue.updated)
            if cycle_changed_pair is not None:
                old_c, new_c = cycle_changed_pair
                await fire_webhooks(
                    self.db,
                    workspace_id=issue.workspace_id,
                    event_type="issue.cycle_changed",
                    data={
                        "id": str(issue.id),
                        "issueCode": issue.issue_code,
                        "title": issue.title,
                        "from": old_c,
                        "to": new_c,
                        "actorUserId": user_id,
                    },
                )
            if estimate_changed_pair is not None:
                old_e, new_e = estimate_changed_pair
                await fire_webhooks(
                    self.db,
                    workspace_id=issue.workspace_id,
                    event_type="issue.estimate_changed",
                    data={
                        "id": str(issue.id),
                        "issueCode": issue.issue_code,
                        "title": issue.title,
                        "from": old_e,
                        "to": new_e,
                        "actorUserId": user_id,
                    },
                )
            if project_changed_pair is not None:
                old_p, new_p = project_changed_pair
                await fire_webhooks(
                    self.db,
                    workspace_id=issue.workspace_id,
                    event_type="issue.project_changed",
                    data={
                        "id": str(issue.id),
                        "issueCode": issue.issue_code,
                        "title": issue.title,
                        "from": old_p,
                        "to": new_p,
                        "actorUserId": user_id,
                    },
                )
        return issue

    async def move_issue_on_board(
        self,
        data: IssueBoardMove,
        user_id: str,
        *,
        workspace_id: str | None = None,
    ) -> Issue:
        """看板拖拽：原子更新 status + position，可选重写目标列 ordered_ids。

        workspace_id 若提供，则要求目标 Issue（及 ordered_ids）属于该工作区。
        """
        issue = await self.get_issue(data.issue_id)
        if not issue:
            raise LookupError("Issue 不存在")
        if workspace_id is not None and issue.workspace_id != workspace_id:
            raise PermissionError("Issue 不属于当前工作区")

        # 主卡片：走 update_issue 以复用 status timeline
        await self.update_issue(
            data.issue_id,
            IssueUpdate(status=data.status, position=data.position),
            user_id,
        )

        if data.ordered_ids:
            # 校验并批量写 position（同事务外再 commit；ordered 项跳过已由 update 写过的主卡亦可再写）
            for idx, oid in enumerate(data.ordered_ids):
                if oid == data.issue_id:
                    # 已写；仍允许校正 position 为序中下标
                    if idx != data.position:
                        await self.db.execute(
                            update(Issue)
                            .where(Issue.id == oid, Issue.is_deleted == False)
                            .values(position=idx, updated_by=user_id)
                        )
                    continue
                other = await self.get_issue(oid)
                if not other:
                    raise LookupError(f"Issue 不存在: {oid}")
                if workspace_id is not None and other.workspace_id != workspace_id:
                    raise PermissionError("ordered_ids 含非本工作区 Issue")
                if other.status != data.status.value and other.status != data.status:
                    # 仅允许重排目标列内卡片；若列表含他列则强制改 status
                    await self.update_issue(
                        oid,
                        IssueUpdate(status=data.status, position=idx),
                        user_id,
                    )
                else:
                    await self.db.execute(
                        update(Issue)
                        .where(Issue.id == oid, Issue.is_deleted == False)
                        .values(position=idx, updated_by=user_id)
                    )
            await self.db.commit()

        moved = await self.get_issue(data.issue_id)
        if not moved:
            raise LookupError("Issue 不存在")
        return moved

    async def delete_issue(self, issue_id: str, user_id: str) -> bool:
        """删除 Issue（软删除）"""
        issue = await self.get_issue(issue_id)
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
        ok = result.rowcount > 0
        if ok and issue:
            await publish_issue_deleted(issue, actor_user_id=user_id)
        return ok

    # ========================================================================
    # 批量操作
    # ========================================================================

    async def bulk_update_issues(
        self,
        data: IssueBulkUpdate,
        user_id: str,
        *,
        workspace_id: str,
    ) -> int:
        """批量更新 Issue（E20：强制 workspace 过滤；支持 cycle_id / tag_ids）"""
        allowed_q = await self.db.execute(
            select(Issue.id).where(
                Issue.id.in_(data.issue_ids),
                Issue.is_deleted == False,  # noqa: E712
                Issue.workspace_id == workspace_id,
            )
        )
        allowed_ids = [row[0] for row in allowed_q.all()]
        if not allowed_ids:
            raise PermissionError("无权批量更新这些 Issue")

        if "cycle_id" in data.model_fields_set:
            await self._validate_cycle_id(
                cycle_id=data.cycle_id,
                workspace_id=workspace_id,
            )

        update_data: Dict[str, Any] = {
            "updated_by": user_id,
            "updated_at": datetime.utcnow(),
        }

        if data.status is not None:
            update_data["status"] = data.status
        if data.priority is not None:
            update_data["priority"] = data.priority
        if data.assignee_id is not None:
            update_data["assignee_id"] = data.assignee_id
        if "cycle_id" in data.model_fields_set:
            update_data["cycle_id"] = data.cycle_id

        field_updates = {
            k: v for k, v in update_data.items() if k not in ("updated_by", "updated_at")
        }
        affected = 0
        if field_updates or True:
            # 始终刷新 updated_*；若仅改标签也会 bump
            query = (
                update(Issue)
                .where(
                    Issue.id.in_(allowed_ids),
                    Issue.is_deleted == False,  # noqa: E712
                )
                .values(**update_data)
            )
            result = await self.db.execute(query)
            affected = result.rowcount or 0

        if data.tag_ids is not None:
            from opentask.services.tag.service import TagService

            tag_svc = TagService(self.db)
            for iid in allowed_ids:
                await tag_svc.replace_issue_tags(
                    issue_id=iid,
                    tag_ids=data.tag_ids,
                    workspace_id=workspace_id,
                    user_id=user_id,
                )
            # replace_issue_tags commits internally; ensure count reflects tag work
            if not field_updates:
                affected = len(allowed_ids)
        else:
            await self.db.commit()

        return int(affected)

    async def relation_block_counts(
        self,
        issue_ids: List[str],
    ) -> Dict[str, Dict[str, int]]:
        """E20：批量统计 blocks / blocked_by 数量。"""
        empty = {iid: {"blocks_count": 0, "blocked_by_count": 0} for iid in issue_ids}
        if not issue_ids:
            return empty

        result = await self.db.execute(
            select(IssueRelation).where(
                or_(
                    IssueRelation.source_id.in_(issue_ids),
                    IssueRelation.target_id.in_(issue_ids),
                )
            )
        )
        rows = list(result.scalars().all())
        for rel in rows:
            rtype = rel.relation_type.value if hasattr(rel.relation_type, "value") else str(rel.relation_type)
            if rel.source_id in empty:
                if rtype == RelationType.BLOCKS.value:
                    empty[rel.source_id]["blocks_count"] += 1
                elif rtype == RelationType.IS_BLOCKED_BY.value:
                    empty[rel.source_id]["blocked_by_count"] += 1
            if rel.target_id in empty:
                if rtype == RelationType.BLOCKS.value:
                    empty[rel.target_id]["blocked_by_count"] += 1
                elif rtype == RelationType.IS_BLOCKED_BY.value:
                    empty[rel.target_id]["blocks_count"] += 1
        return empty

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
        # E52：flush 以拿到 comment.id，供 timeline / Activity 反应摘要挂载
        await self.db.flush()

        # 更新 Issue 评论计数
        await self._increment_comment_count(issue_id)

        # 添加时间线记录
        await self._add_timeline(
            issue_id=issue_id,
            action_type=TimelineAction.COMMENTED,
            user_id=user_id,
            action_data={"comment_id": comment.id, "parent_id": parent_id},
        )

        # E48：非创建者首评 → first_response clocks met（同事务）
        issue = await self.get_issue(issue_id)
        if issue is not None:
            await SlaService(self.db).mark_first_response(
                issue=issue, actor_user_id=user_id
            )

        await self.db.commit()
        # 注释掉 refresh 以避免枚举值问题
        # await self.db.refresh(comment)

        # Inbox：评论 / @mention 通知（非作者）；自动化 → automation_comment
        if issue is None:
            issue = await self.get_issue(issue_id)
        if issue:
            meta = meta_data or {}
            is_automation = (
                str(comment_type).lower() in ("system", "commenttype.system")
                or meta.get("source") == "automation"
            )
            await NotificationService(self.db).notify_comment(
                issue,
                actor_user_id=user_id,
                comment_content=content,
                comment_id=comment.id,
                base_type="automation_comment" if is_automation else "commented",
            )
            await publish_comment_created(
                workspace_id=issue.workspace_id,
                issue_id=issue_id,
                comment_id=str(comment.id),
                issue_code=issue.issue_code,
                actor_user_id=user_id,
            )
            await fire_webhooks(
                self.db,
                workspace_id=issue.workspace_id,
                event_type="comment.created",
                data={
                    "id": str(comment.id),
                    "issueId": str(issue_id),
                    "issueCode": issue.issue_code,
                },
            )
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
        """获取 Issue 的所有标签关联行"""
        query = select(IssueTag).where(IssueTag.issue_id == issue_id)
        result = await self.db.execute(query)
        return list(result.scalars().all())

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
    # 评论反应（E27）
    # ========================================================================

    async def get_comment_reactions(self, comment_id: str) -> List["CommentReaction"]:
        from opentask.models.issue.model import CommentReaction

        result = await self.db.execute(
            select(CommentReaction)
            .where(CommentReaction.comment_id == comment_id)
            .order_by(CommentReaction.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_comment_reaction_map(self, comment_id: str) -> Dict[str, List[str]]:
        reactions = await self.get_comment_reactions(comment_id)
        out: Dict[str, List[str]] = {}
        for r in reactions:
            out.setdefault(r.emoji, []).append(r.user_id)
        return out

    async def get_comments_reaction_maps(
        self, comment_ids: List[str]
    ) -> Dict[str, Dict[str, List[str]]]:
        from opentask.models.issue.model import CommentReaction

        if not comment_ids:
            return {}
        result = await self.db.execute(
            select(CommentReaction).where(CommentReaction.comment_id.in_(comment_ids))
        )
        out: Dict[str, Dict[str, List[str]]] = {cid: {} for cid in comment_ids}
        for r in result.scalars().all():
            out.setdefault(r.comment_id, {}).setdefault(r.emoji, []).append(r.user_id)
        return out

    async def add_comment_reaction(
        self, comment_id: str, emoji: str, user_id: str
    ) -> "CommentReaction":
        from opentask.models.issue.model import CommentReaction

        result = await self.db.execute(
            select(CommentReaction).where(
                and_(
                    CommentReaction.comment_id == comment_id,
                    CommentReaction.emoji == emoji,
                    CommentReaction.user_id == user_id,
                )
            )
        )
        existing = result.scalar_one_or_none()
        if existing:
            return existing
        reaction = CommentReaction(
            comment_id=comment_id,
            emoji=emoji,
            user_id=user_id,
        )
        self.db.add(reaction)
        await self.db.commit()
        await self.db.refresh(reaction)
        return reaction

    async def remove_comment_reaction(
        self, comment_id: str, emoji: str, user_id: str
    ) -> bool:
        from opentask.models.issue.model import CommentReaction

        result = await self.db.execute(
            delete(CommentReaction).where(
                and_(
                    CommentReaction.comment_id == comment_id,
                    CommentReaction.emoji == emoji,
                    CommentReaction.user_id == user_id,
                )
            )
        )
        await self.db.commit()
        return bool(result.rowcount)


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
