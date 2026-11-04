"""Inbox 通知服务（E3-S3）"""
from __future__ import annotations

import re
from datetime import datetime
from typing import Iterable, Optional

from sqlalchemy import and_, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from opentask.models.issue.model import Issue
from opentask.models.notification.model import Notification
from opentask.models.user.model import UserModel
from opentask.models.workspace.model import WorkspaceMember

# @username 或 @uuid；捕获 token（不含 @）
_MENTION_RE = re.compile(r"@([A-Za-z0-9_.-]{1,64})")


class NotificationService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(
        self,
        *,
        workspace_id: str,
        recipient_user_id: str,
        actor_user_id: Optional[str],
        type: str,
        resource_type: str,
        resource_id: str,
        title: str,
        body: Optional[str] = None,
    ) -> Optional[Notification]:
        """创建通知；若 recipient==actor 则跳过。"""
        if not recipient_user_id:
            return None
        if actor_user_id and str(recipient_user_id) == str(actor_user_id):
            return None
        row = Notification(
            workspace_id=workspace_id,
            recipient_user_id=str(recipient_user_id),
            actor_user_id=str(actor_user_id) if actor_user_id else None,
            type=type,
            resource_type=resource_type,
            resource_id=resource_id,
            title=title[:255],
            body=body,
        )
        self.db.add(row)
        return row

    async def notify_assigned(
        self,
        issue: Issue,
        *,
        actor_user_id: str,
        new_assignee_id: Optional[str],
    ) -> Optional[Notification]:
        """指派：通知新负责人；并 fanout 给 watchers（subscribed_update）。"""
        created: list[Notification] = []
        if new_assignee_id and issue.workspace_id:
            title = f"你被指派到「{issue.title}」"
            body = f"Issue {issue.issue_code or issue.id}"
            n = await self.create(
                workspace_id=issue.workspace_id,
                recipient_user_id=new_assignee_id,
                actor_user_id=actor_user_id,
                type="assigned",
                resource_type="issue",
                resource_id=issue.id,
                title=title,
                body=body,
            )
            if n:
                created.append(n)

        watcher_notes = await self.notify_watchers(
            issue,
            actor_user_id=actor_user_id,
            type="subscribed_update",
            title=f"「{issue.title}」负责人已更新",
            body=f"Issue {issue.issue_code or issue.id}",
            exclude_user_ids={str(new_assignee_id)} if new_assignee_id else set(),
            commit=False,
        )
        created.extend(watcher_notes)
        if created:
            await self.db.commit()
        return created[0] if created else None

    async def notify_comment(
        self,
        issue: Issue,
        *,
        actor_user_id: str,
        comment_content: str,
        comment_id: Optional[str] = None,
    ) -> list[Notification]:
        """评论：通知 assignee/reporter（非作者）+ @mention 工作区成员。"""
        if not issue.workspace_id:
            return []

        snippet = (comment_content or "").strip()
        if len(snippet) > 200:
            snippet = snippet[:200] + "…"

        recipients: dict[str, str] = {}  # user_id -> type

        for uid in (issue.assignee_id, issue.reporter_id):
            if uid and str(uid) != str(actor_user_id):
                recipients[str(uid)] = "commented"

        # E18：关注者也收评论（mention 优先）
        for uid in await self._watcher_ids(issue.id):
            if uid != str(actor_user_id):
                recipients.setdefault(uid, "commented")

        mentioned = await self._resolve_mentions(
            issue.workspace_id, comment_content or "", actor_user_id=actor_user_id
        )
        for uid in mentioned:
            # mention 优先覆盖 commented，便于区分类型
            recipients[uid] = "mentioned"

        created: list[Notification] = []
        for uid, ntype in recipients.items():
            if ntype == "mentioned":
                title = f"有人在「{issue.title}」中提到了你"
            else:
                title = f"「{issue.title}」有新评论"
            n = await self.create(
                workspace_id=issue.workspace_id,
                recipient_user_id=uid,
                actor_user_id=actor_user_id,
                type=ntype,
                resource_type="issue",
                resource_id=issue.id,
                title=title,
                body=snippet or None,
            )
            if n:
                created.append(n)

        if created:
            await self.db.commit()
        return created


    async def _watcher_ids(self, issue_id: str) -> list[str]:
        from opentask.services.issue_watcher.service import IssueWatcherService

        return await IssueWatcherService(self.db).user_ids(issue_id=issue_id)

    async def notify_watchers(
        self,
        issue: Issue,
        *,
        actor_user_id: str,
        type: str,
        title: str,
        body: Optional[str] = None,
        exclude_user_ids: Optional[set[str]] = None,
        commit: bool = True,
    ) -> list[Notification]:
        """Fanout to issue watchers; skips actor and exclude set."""
        if not issue.workspace_id:
            return []
        exclude = {str(x) for x in (exclude_user_ids or set()) if x}
        exclude.add(str(actor_user_id))
        created: list[Notification] = []
        for uid in await self._watcher_ids(issue.id):
            if uid in exclude:
                continue
            n = await self.create(
                workspace_id=issue.workspace_id,
                recipient_user_id=uid,
                actor_user_id=actor_user_id,
                type=type,
                resource_type="issue",
                resource_id=issue.id,
                title=title,
                body=body,
            )
            if n:
                created.append(n)
        if created and commit:
            await self.db.commit()
        return created

    async def notify_status_changed(
        self,
        issue: Issue,
        *,
        actor_user_id: str,
        old_status: Optional[str],
        new_status: str,
    ) -> list[Notification]:
        if not issue.workspace_id:
            return []
        body = f"{old_status or '?'} → {new_status}"
        title = f"「{issue.title}」状态已更新"
        return await self.notify_watchers(
            issue,
            actor_user_id=actor_user_id,
            type="status_changed",
            title=title,
            body=body,
        )

    async def notify_due_date_changed(
        self,
        issue: Issue,
        *,
        actor_user_id: str,
        old_due=None,
        new_due=None,
    ) -> list[Notification]:
        """E19：due_date 变更 → assignee + watchers（跳过 actor）。"""
        if not issue.workspace_id:
            return []

        def _fmt(v):
            if v is None:
                return "—"
            if hasattr(v, "isoformat"):
                try:
                    return v.isoformat()[:10]
                except Exception:
                    return str(v)[:10]
            return str(v)[:10]

        body = f"{_fmt(old_due)} → {_fmt(new_due)}"
        title = f"「{issue.title}」截止日期已更新"
        created: list[Notification] = []

        if issue.assignee_id and str(issue.assignee_id) != str(actor_user_id):
            n = await self.create(
                workspace_id=issue.workspace_id,
                recipient_user_id=str(issue.assignee_id),
                actor_user_id=actor_user_id,
                type="due_date_changed",
                resource_type="issue",
                resource_id=issue.id,
                title=title,
                body=body,
            )
            if n:
                created.append(n)

        exclude = {str(issue.assignee_id)} if issue.assignee_id else set()
        watcher_notes = await self.notify_watchers(
            issue,
            actor_user_id=actor_user_id,
            type="due_date_changed",
            title=title,
            body=body,
            exclude_user_ids=exclude,
            commit=False,
        )
        created.extend(watcher_notes)
        if created:
            await self.db.commit()
        return created

    async def _resolve_mentions(
        self, workspace_id: str, content: str, *, actor_user_id: str
    ) -> set[str]:
        tokens = {m.group(1) for m in _MENTION_RE.finditer(content)}
        if not tokens:
            return set()

        # 工作区成员
        mem_q = await self.db.execute(
            select(WorkspaceMember.user_id).where(WorkspaceMember.workspace_id == workspace_id)
        )
        member_ids = {str(r) for r in mem_q.scalars().all()}
        if not member_ids:
            return set()

        # 直接按 userId token
        hit: set[str] = {t for t in tokens if t in member_ids}

        # 按 username 解析
        name_tokens = tokens - hit
        if name_tokens:
            users_q = await self.db.execute(
                select(UserModel).where(UserModel.username.in_(list(name_tokens)))
            )
            for u in users_q.scalars().all():
                uid = str(u.id)
                if uid in member_ids:
                    hit.add(uid)

        hit.discard(str(actor_user_id))
        return hit

    def _visible_snooze_clause(self, *, include_snoozed: bool, now: datetime):
        if include_snoozed:
            return None
        return or_(
            Notification.snoozed_until.is_(None),
            Notification.snoozed_until <= now,
        )

    async def list_for_user(
        self,
        user_id: str,
        *,
        workspace_id: Optional[str] = None,
        unread_only: bool = False,
        include_snoozed: bool = False,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[Notification], int, int]:
        page = max(1, page)
        page_size = min(max(1, page_size), 100)
        now = datetime.utcnow()

        conds = [Notification.recipient_user_id == str(user_id)]
        if workspace_id:
            conds.append(Notification.workspace_id == workspace_id)
        if unread_only:
            conds.append(Notification.read_at.is_(None))
        snooze_clause = self._visible_snooze_clause(include_snoozed=include_snoozed, now=now)
        if snooze_clause is not None:
            conds.append(snooze_clause)

        where = and_(*conds)
        total = (
            await self.db.execute(select(func.count()).select_from(Notification).where(where))
        ).scalar_one()

        unread_conds = [
            Notification.recipient_user_id == str(user_id),
            Notification.read_at.is_(None),
        ]
        if workspace_id:
            unread_conds.append(Notification.workspace_id == workspace_id)
        if snooze_clause is not None:
            unread_conds.append(snooze_clause)
        unread_count = (
            await self.db.execute(
                select(func.count()).select_from(Notification).where(and_(*unread_conds))
            )
        ).scalar_one()

        rows_q = (
            select(Notification)
            .where(where)
            .order_by(Notification.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        rows = list((await self.db.execute(rows_q)).scalars().all())
        return rows, int(total), int(unread_count)

    async def mark_read(self, notification_id: str, user_id: str) -> Optional[Notification]:
        q = await self.db.execute(
            select(Notification).where(
                Notification.id == notification_id,
                Notification.recipient_user_id == str(user_id),
            )
        )
        row = q.scalar_one_or_none()
        if not row:
            return None
        if row.read_at is None:
            row.read_at = datetime.utcnow()
            await self.db.commit()
            await self.db.refresh(row)
        return row

    async def mark_all_read(self, user_id: str, *, workspace_id: Optional[str] = None) -> int:
        conds = [
            Notification.recipient_user_id == str(user_id),
            Notification.read_at.is_(None),
        ]
        if workspace_id:
            conds.append(Notification.workspace_id == workspace_id)
        result = await self.db.execute(
            update(Notification)
            .where(and_(*conds))
            .values(read_at=datetime.utcnow())
        )
        await self.db.commit()
        return int(result.rowcount or 0)


    async def get_for_recipient(
        self, notification_id: str, user_id: str
    ) -> Optional[Notification]:
        q = await self.db.execute(
            select(Notification).where(
                Notification.id == notification_id,
                Notification.recipient_user_id == str(user_id),
            )
        )
        return q.scalar_one_or_none()

    async def snooze(
        self, notification_id: str, user_id: str, *, until: datetime
    ) -> Optional[Notification]:
        row = await self.get_for_recipient(notification_id, user_id)
        if not row:
            return None
        row.snoozed_until = until
        await self.db.commit()
        await self.db.refresh(row)
        return row

    async def unsnooze(self, notification_id: str, user_id: str) -> Optional[Notification]:
        row = await self.get_for_recipient(notification_id, user_id)
        if not row:
            return None
        row.snoozed_until = None
        await self.db.commit()
        await self.db.refresh(row)
        return row


def serialize_notification(n: Notification) -> dict:
    return {
        "id": n.id,
        "workspaceId": n.workspace_id,
        "recipientUserId": n.recipient_user_id,
        "actorUserId": n.actor_user_id,
        "type": n.type,
        "resourceType": n.resource_type,
        "resourceId": n.resource_id,
        "title": n.title,
        "body": n.body,
        "readAt": n.read_at,
        "snoozedUntil": n.snoozed_until,
        "createdAt": n.created_at,
    }
