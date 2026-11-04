"""Inbox 通知服务（E3-S3）"""
from __future__ import annotations

import re
from datetime import date, datetime, timedelta
from typing import Iterable, Optional

from sqlalchemy import and_, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from opentask.models.issue.model import Issue
from opentask.models.notification.model import Notification
from opentask.models.due_reminder_delivery.model import (
    DueReminderDelivery,
    make_dedupe_key,
)
from opentask.models.issue_watcher.model import IssueWatcher
from opentask.models.issue.enums import IssueStatus
from opentask.models.notification_preference.model import (
    PREF_KEYS,
    TYPE_TO_PREF_KEY,
    NotificationPreference,
)
from opentask.models.user.model import UserModel
from opentask.models.workspace.model import WorkspaceMember
from opentask.services.workspace_realtime import publish_inbox_created
from opentask.services.email import (
    email_configured,
    resolve_recipient_email,
    send_notification_email,
)

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
        """创建通知；若 recipient==actor 则跳过；尊重通知偏好（E27）。"""
        if not recipient_user_id:
            return None
        if actor_user_id and str(recipient_user_id) == str(actor_user_id):
            return None
        if not await self.is_type_enabled(
            workspace_id=workspace_id,
            user_id=str(recipient_user_id),
            notif_type=type,
        ):
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
        try:
            await self.db.flush()
        except Exception:
            # flush 失败则交给调用方事务；不阻塞主路径
            return row
        await publish_inbox_created(row, actor_user_id=actor_user_id)
        # E30：best-effort 出站邮件（失败不影响 Inbox）
        await self._maybe_send_email(row)
        return row

    def default_prefs_dict(self) -> dict:
        return {k: True for k in PREF_KEYS}

    def serialize_prefs(
        self, row: Optional[NotificationPreference], *, user_id: str, workspace_id: str
    ) -> dict:
        base = self.default_prefs_dict()
        out = {
            "userId": user_id,
            "workspaceId": workspace_id,
            **base,
            "due_reminder_digest": False,
            "insights_digest": False,
            "email_enabled": False,
            "email_configured": email_configured(),
        }
        if row is None:
            return out
        for k in PREF_KEYS:
            out[k] = bool(getattr(row, k))
        out["due_reminder_digest"] = bool(getattr(row, "due_reminder_digest", False))
        out["insights_digest"] = bool(getattr(row, "insights_digest", False))
        out["email_enabled"] = bool(getattr(row, "email_enabled", False))
        return out

    async def get_prefs(
        self, *, user_id: str, workspace_id: str
    ) -> Optional[NotificationPreference]:
        q = await self.db.execute(
            select(NotificationPreference).where(
                NotificationPreference.user_id == str(user_id),
                NotificationPreference.workspace_id == workspace_id,
            )
        )
        return q.scalar_one_or_none()

    async def get_prefs_payload(self, *, user_id: str, workspace_id: str) -> dict:
        row = await self.get_prefs(user_id=user_id, workspace_id=workspace_id)
        return self.serialize_prefs(row, user_id=str(user_id), workspace_id=workspace_id)

    async def upsert_prefs(
        self, *, user_id: str, workspace_id: str, updates: dict
    ) -> NotificationPreference:
        row = await self.get_prefs(user_id=user_id, workspace_id=workspace_id)
        if row is None:
            row = NotificationPreference(
                user_id=str(user_id),
                workspace_id=workspace_id,
            )
            self.db.add(row)
        for k in PREF_KEYS:
            if k in updates and updates[k] is not None:
                setattr(row, k, bool(updates[k]))
        if "due_reminder_digest" in updates and updates["due_reminder_digest"] is not None:
            row.due_reminder_digest = bool(updates["due_reminder_digest"])
        if "insights_digest" in updates and updates["insights_digest"] is not None:
            row.insights_digest = bool(updates["insights_digest"])
        if "email_enabled" in updates and updates["email_enabled"] is not None:
            row.email_enabled = bool(updates["email_enabled"])
        row.updated_at = datetime.utcnow()
        await self.db.commit()
        await self.db.refresh(row)
        return row

    async def is_type_enabled(
        self, *, workspace_id: str, user_id: str, notif_type: str
    ) -> bool:
        """Unknown types fail-open (still create)."""
        pref_key = TYPE_TO_PREF_KEY.get(notif_type)
        if not pref_key:
            return True
        row = await self.get_prefs(user_id=user_id, workspace_id=workspace_id)
        if row is None:
            return True
        return bool(getattr(row, pref_key, True))

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
        base_type: str = "commented",
    ) -> list[Notification]:
        """评论：通知 assignee/reporter（非作者）+ @mention 工作区成员。

        base_type: normally "commented"; automation/system → "automation_comment".
        Mentions always use type "mentioned".
        """
        if not issue.workspace_id:
            return []

        snippet = (comment_content or "").strip()
        if len(snippet) > 200:
            snippet = snippet[:200] + "…"

        comment_type = base_type if base_type in ("commented", "automation_comment") else "commented"

        recipients: dict[str, str] = {}  # user_id -> type

        for uid in (issue.assignee_id, issue.reporter_id):
            if uid and str(uid) != str(actor_user_id):
                recipients[str(uid)] = comment_type

        # E18：关注者也收评论（mention 优先）
        for uid in await self._watcher_ids(issue.id):
            if uid != str(actor_user_id):
                recipients.setdefault(uid, comment_type)

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
            elif ntype == "automation_comment":
                title = f"「{issue.title}」有自动化评论"
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



    async def is_email_enabled(self, *, workspace_id: str, user_id: str) -> bool:
        """Channel toggle; no row → False (opt-in)."""
        row = await self.get_prefs(user_id=user_id, workspace_id=workspace_id)
        if row is None:
            return False
        return bool(getattr(row, "email_enabled", False))

    async def _maybe_send_email(self, row: Notification) -> None:
        """After inbox create: email_enabled + configured + recipient address."""
        try:
            if not email_configured():
                return
            if not await self.is_email_enabled(
                workspace_id=row.workspace_id, user_id=str(row.recipient_user_id)
            ):
                return
            uq = await self.db.execute(
                select(UserModel).where(UserModel.id == str(row.recipient_user_id))
            )
            user = uq.scalar_one_or_none()
            to = resolve_recipient_email(user)
            if not to:
                return
            await send_notification_email(
                to=to,
                title=row.title or "",
                body=row.body,
                notif_type=row.type,
                resource_type=row.resource_type,
                resource_id=row.resource_id,
            )
        except Exception:
            # never break inbox path
            import logging

            logging.getLogger(__name__).exception(
                "email hook failed notif=%s", getattr(row, "id", None)
            )


    LEAD_DAYS = 3
    CLOSED_STATUSES = {
        IssueStatus.CLOSED.value,
        IssueStatus.RESOLVED.value,
        IssueStatus.REJECTED.value,
    }

    def _as_date(self, value) -> Optional[date]:
        if value is None:
            return None
        if isinstance(value, datetime):
            return value.date()
        if isinstance(value, date):
            return value
        return None

    async def _watcher_ids(self, issue_id: str) -> list[str]:
        q = await self.db.execute(
            select(IssueWatcher.user_id).where(IssueWatcher.issue_id == issue_id)
        )
        return [str(uid) for uid in q.scalars().all()]

    def _recipients_for_issue(self, issue: Issue, watcher_ids: list[str]) -> list[str]:
        ids: set[str] = set()
        if issue.assignee_id:
            ids.add(str(issue.assignee_id))
        for uid in watcher_ids:
            ids.add(str(uid))
        return sorted(ids)

    async def _delivery_exists(self, *, workspace_id: str, dedupe_key: str) -> bool:
        q = await self.db.execute(
            select(DueReminderDelivery.id).where(
                DueReminderDelivery.workspace_id == workspace_id,
                DueReminderDelivery.dedupe_key == dedupe_key,
            )
        )
        return q.scalar_one_or_none() is not None

    async def _insert_delivery(
        self,
        *,
        workspace_id: str,
        issue_id: Optional[str],
        user_id: str,
        kind: str,
        bucket_date: date,
        due_date_bucket: Optional[date],
        notification_id: Optional[str],
    ) -> DueReminderDelivery:
        key = make_dedupe_key(
            kind=kind,
            user_id=str(user_id),
            issue_id=issue_id,
            bucket_date=bucket_date,
            due_date_bucket=due_date_bucket,
        )
        row = DueReminderDelivery(
            workspace_id=workspace_id,
            issue_id=issue_id,
            user_id=str(user_id),
            kind=kind,
            bucket_date=bucket_date,
            due_date_bucket=due_date_bucket,
            dedupe_key=key,
            notification_id=notification_id,
        )
        self.db.add(row)
        try:
            await self.db.flush()
        except Exception:
            await self.db.rollback()
            raise
        return row

    def _format_due_title(self, issue: Issue, kind: str) -> str:
        code = issue.issue_code or issue.id
        if kind == "overdue":
            return f"已逾期：{code} {issue.title}"
        return f"即将到期：{code} {issue.title}"

    def _format_due_body(self, issue: Issue, kind: str, due_d: date) -> str:
        label = "逾期" if kind == "overdue" else "到期"
        return f"{label}日 {due_d.isoformat()} · Issue {issue.issue_code or issue.id}"

    def _format_digest_body(self, items: list[tuple[str, Issue, date]]) -> str:
        soon_lines = []
        overdue_lines = []
        for kind, issue, due_d in items:
            line = f"- {issue.issue_code or issue.id} {issue.title} (due {due_d.isoformat()})"
            if kind == "overdue":
                overdue_lines.append(line)
            else:
                soon_lines.append(line)
        parts = []
        if overdue_lines:
            parts.append("已逾期:\n" + "\n".join(overdue_lines))
        if soon_lines:
            parts.append("即将到期:\n" + "\n".join(soon_lines))
        return "\n\n".join(parts) if parts else ""

    async def run_due_reminders(
        self,
        *,
        workspace_id: str,
        actor_user_id: Optional[str] = None,
        today: Optional[date] = None,
    ) -> dict:
        """External tick: soon/overdue Inbox (+ optional digest). No in-process cron."""
        today = today or datetime.utcnow().date()
        lead_end = today + timedelta(days=self.LEAD_DAYS)

        q = await self.db.execute(
            select(Issue).where(
                Issue.workspace_id == workspace_id,
                Issue.due_date.isnot(None),
                Issue.status.notin_(list(self.CLOSED_STATUSES)),
            )
        )
        issues = list(q.scalars().all())

        processed = 0
        reminders_created = 0
        digests_created = 0
        skipped = 0
        errors: list[dict] = []
        # user_id -> list[(kind, issue, due_d)]
        buffers: dict[str, list[tuple[str, Issue, date]]] = {}

        for issue in issues:
            due_d = self._as_date(issue.due_date)
            if due_d is None:
                continue
            if due_d < today:
                kind = "overdue"
            elif today <= due_d <= lead_end:
                kind = "soon"
            else:
                continue
            processed += 1
            watchers = await self._watcher_ids(issue.id)
            recipients = self._recipients_for_issue(issue, watchers)
            if not recipients:
                skipped += 1
                continue

            for user_id in recipients:
                try:
                    prefs_row = await self.get_prefs(
                        user_id=user_id, workspace_id=workspace_id
                    )
                    due_on = True if prefs_row is None else bool(
                        getattr(prefs_row, "due_reminder", True)
                    )
                    digest_on = False if prefs_row is None else bool(
                        getattr(prefs_row, "due_reminder_digest", False)
                    )
                    if not due_on:
                        skipped += 1
                        continue
                    if digest_on:
                        buffers.setdefault(user_id, []).append((kind, issue, due_d))
                        continue

                    dedupe = make_dedupe_key(
                        kind=kind,
                        user_id=user_id,
                        issue_id=issue.id,
                        bucket_date=today,
                        due_date_bucket=due_d if kind == "soon" else None,
                    )
                    if await self._delivery_exists(
                        workspace_id=workspace_id, dedupe_key=dedupe
                    ):
                        skipped += 1
                        continue

                    n = await self.create(
                        workspace_id=workspace_id,
                        recipient_user_id=user_id,
                        actor_user_id=None,  # system tick — never self-skip
                        type="due_reminder",
                        resource_type="issue",
                        resource_id=issue.id,
                        title=self._format_due_title(issue, kind),
                        body=self._format_due_body(issue, kind, due_d),
                    )
                    if n is None:
                        skipped += 1
                        continue
                    await self._insert_delivery(
                        workspace_id=workspace_id,
                        issue_id=issue.id,
                        user_id=user_id,
                        kind=kind,
                        bucket_date=today,
                        due_date_bucket=due_d if kind == "soon" else None,
                        notification_id=getattr(n, "id", None),
                    )
                    reminders_created += 1
                except Exception as e:
                    errors.append(
                        {
                            "issueId": issue.id,
                            "userId": user_id,
                            "kind": kind,
                            "message": str(e)[:500],
                        }
                    )

        for user_id, items in buffers.items():
            try:
                digest_key = make_dedupe_key(
                    kind="digest",
                    user_id=user_id,
                    issue_id=None,
                    bucket_date=today,
                    due_date_bucket=None,
                )
                if await self._delivery_exists(
                    workspace_id=workspace_id, dedupe_key=digest_key
                ):
                    skipped += 1
                    continue
                body = self._format_digest_body(items)
                title = f"今日到期提醒 ({len(items)})"
                n = await self.create(
                    workspace_id=workspace_id,
                    recipient_user_id=user_id,
                    actor_user_id=None,
                    type="due_reminder_digest",
                    resource_type="workspace",
                    resource_id=workspace_id,
                    title=title,
                    body=body,
                )
                if n is None:
                    skipped += 1
                    continue
                await self._insert_delivery(
                    workspace_id=workspace_id,
                    issue_id=None,
                    user_id=user_id,
                    kind="digest",
                    bucket_date=today,
                    due_date_bucket=None,
                    notification_id=getattr(n, "id", None),
                )
                digests_created += 1
            except Exception as e:
                errors.append(
                    {
                        "issueId": None,
                        "userId": user_id,
                        "kind": "digest",
                        "message": str(e)[:500],
                    }
                )

        try:
            await self.db.commit()
        except Exception:
            await self.db.rollback()
            raise

        return {
            "processedIssues": processed,
            "remindersCreated": reminders_created,
            "digestsCreated": digests_created,
            "skipped": skipped,
            "errors": errors,
        }

    async def list_due_reminder_deliveries(
        self,
        *,
        workspace_id: str,
        bucket_date: Optional[date] = None,
        limit: int = 100,
    ) -> list[DueReminderDelivery]:
        limit = max(1, min(int(limit or 100), 100))
        stmt = select(DueReminderDelivery).where(
            DueReminderDelivery.workspace_id == workspace_id
        )
        if bucket_date is not None:
            stmt = stmt.where(DueReminderDelivery.bucket_date == bucket_date)
        stmt = stmt.order_by(DueReminderDelivery.created_at.desc()).limit(limit)
        q = await self.db.execute(stmt)
        return list(q.scalars().all())



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


__all_pref_keys__ = PREF_KEYS
