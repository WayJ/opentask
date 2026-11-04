"""SLA policies + clocks + run-due (E42)."""
from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any, Optional

from fastapi import HTTPException, status as http_status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from opentask.models.issue.enums import IssueStatus
from opentask.models.issue.model import Issue
from opentask.models.issue_watcher.model import IssueWatcher
from opentask.models.sla.model import (
    CLOSED_STOP_STATUSES,
    DEFAULT_TARGET_MINUTES,
    IssueSlaClock,
    SLA_METRICS,
    SlaPolicy,
    TARGET_MINUTES_MAX,
    TARGET_MINUTES_MIN,
)
from opentask.models.workspace.model import WorkspaceMember
from opentask.services.notification.service import NotificationService
from opentask.services.workspace_webhook.service import fire_webhooks

logger = logging.getLogger(__name__)

_KNOWN_STATUSES = frozenset(s.value for s in IssueStatus)


def require_writer(member: WorkspaceMember) -> None:
    if member.role not in ("owner", "member"):
        raise HTTPException(
            status_code=http_status.HTTP_403_FORBIDDEN,
            detail="仅 member/owner 可写",
        )


def require_owner(member: WorkspaceMember) -> None:
    if member.role != "owner":
        raise HTTPException(
            status_code=http_status.HTTP_403_FORBIDDEN,
            detail="仅 owner 可管理 SLA 策略",
        )


def _status_str(v: Any) -> str:
    return str(getattr(v, "value", v))


def serialize_policy(row: SlaPolicy) -> dict:
    return {
        "id": row.id,
        "workspaceId": row.workspace_id,
        "name": row.name,
        "enabled": bool(row.enabled),
        "metric": row.metric,
        "startStatuses": list(row.start_statuses or []),
        "stopStatuses": list(row.stop_statuses or []),
        "targetMinutes": int(row.target_minutes),
        "notifyAssignee": bool(row.notify_assignee),
        "notifyWatchers": bool(row.notify_watchers),
        "createdAt": row.created_at.isoformat() if row.created_at else None,
        "updatedAt": row.updated_at.isoformat() if row.updated_at else None,
    }


def serialize_clock(row: IssueSlaClock, *, policy_name: Optional[str] = None) -> dict:
    return {
        "id": row.id,
        "workspaceId": row.workspace_id,
        "issueId": row.issue_id,
        "policyId": row.policy_id,
        "policyName": policy_name,
        "status": row.status,
        "startedAt": row.started_at.isoformat() if row.started_at else None,
        "deadlineAt": row.deadline_at.isoformat() if row.deadline_at else None,
        "stoppedAt": row.stopped_at.isoformat() if row.stopped_at else None,
        "breachedAt": row.breached_at.isoformat() if row.breached_at else None,
        "startStatus": row.start_status,
    }


def _validate_statuses(values: list[str], *, field: str, allow_empty: bool) -> list[str]:
    if not isinstance(values, list):
        raise HTTPException(status_code=400, detail=f"{field} 必须是数组")
    out = [str(v) for v in values]
    if not allow_empty and not out:
        raise HTTPException(status_code=400, detail=f"{field} 不能为空")
    unknown = [v for v in out if v not in _KNOWN_STATUSES]
    if unknown:
        raise HTTPException(status_code=400, detail=f"非法 status: {unknown}")
    return out


def _validate_target(minutes: int) -> int:
    m = int(minutes)
    if m < TARGET_MINUTES_MIN or m > TARGET_MINUTES_MAX:
        raise HTTPException(
            status_code=400,
            detail=f"targetMinutes 须在 {TARGET_MINUTES_MIN}…{TARGET_MINUTES_MAX}",
        )
    return m


def _should_stop(policy: SlaPolicy, new_status: str) -> bool:
    stops = list(policy.stop_statuses or [])
    if stops:
        return new_status in stops
    return new_status in CLOSED_STOP_STATUSES


class SlaService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_policies(self, *, workspace_id: str) -> list[SlaPolicy]:
        q = await self.db.execute(
            select(SlaPolicy)
            .where(SlaPolicy.workspace_id == workspace_id)
            .order_by(SlaPolicy.created_at.asc())
        )
        return list(q.scalars().all())

    async def get_policy(self, *, workspace_id: str, policy_id: str) -> SlaPolicy:
        q = await self.db.execute(
            select(SlaPolicy).where(
                SlaPolicy.id == policy_id,
                SlaPolicy.workspace_id == workspace_id,
            )
        )
        row = q.scalar_one_or_none()
        if not row:
            raise HTTPException(status_code=404, detail="SLA 策略不存在")
        return row

    async def create_policy(
        self,
        *,
        workspace_id: str,
        name: str,
        start_statuses: list[str],
        stop_statuses: Optional[list[str]] = None,
        target_minutes: int = DEFAULT_TARGET_MINUTES,
        metric: str = "time_in_status",
        notify_assignee: bool = True,
        notify_watchers: bool = False,
        enabled: bool = True,
    ) -> SlaPolicy:
        name = (name or "").strip()
        if not name or len(name) > 80:
            raise HTTPException(status_code=400, detail="name 长度 1…80")
        if metric not in SLA_METRICS:
            raise HTTPException(status_code=400, detail=f"不支持的 metric: {metric}")
        starts = _validate_statuses(start_statuses, field="startStatuses", allow_empty=False)
        stops = _validate_statuses(stop_statuses or [], field="stopStatuses", allow_empty=True)
        minutes = _validate_target(target_minutes)
        row = SlaPolicy(
            workspace_id=workspace_id,
            name=name,
            enabled=bool(enabled),
            metric=metric,
            start_statuses=starts,
            stop_statuses=stops,
            target_minutes=minutes,
            notify_assignee=bool(notify_assignee),
            notify_watchers=bool(notify_watchers),
        )
        self.db.add(row)
        await self.db.commit()
        await self.db.refresh(row)
        return row

    async def update_policy(
        self,
        *,
        workspace_id: str,
        policy_id: str,
        updates: dict[str, Any],
    ) -> SlaPolicy:
        row = await self.get_policy(workspace_id=workspace_id, policy_id=policy_id)
        if "name" in updates and updates["name"] is not None:
            name = str(updates["name"]).strip()
            if not name or len(name) > 80:
                raise HTTPException(status_code=400, detail="name 长度 1…80")
            row.name = name
        if "enabled" in updates and updates["enabled"] is not None:
            row.enabled = bool(updates["enabled"])
        if "metric" in updates and updates["metric"] is not None:
            if updates["metric"] not in SLA_METRICS:
                raise HTTPException(status_code=400, detail="不支持的 metric")
            row.metric = updates["metric"]
        if "startStatuses" in updates and updates["startStatuses"] is not None:
            row.start_statuses = _validate_statuses(
                updates["startStatuses"], field="startStatuses", allow_empty=False
            )
        if "stopStatuses" in updates and updates["stopStatuses"] is not None:
            row.stop_statuses = _validate_statuses(
                updates["stopStatuses"], field="stopStatuses", allow_empty=True
            )
        if "targetMinutes" in updates and updates["targetMinutes"] is not None:
            row.target_minutes = _validate_target(updates["targetMinutes"])
        if "notifyAssignee" in updates and updates["notifyAssignee"] is not None:
            row.notify_assignee = bool(updates["notifyAssignee"])
        if "notifyWatchers" in updates and updates["notifyWatchers"] is not None:
            row.notify_watchers = bool(updates["notifyWatchers"])
        row.updated_at = datetime.utcnow()
        await self.db.commit()
        await self.db.refresh(row)
        return row

    async def delete_policy(self, *, workspace_id: str, policy_id: str) -> None:
        row = await self.get_policy(workspace_id=workspace_id, policy_id=policy_id)
        await self.db.delete(row)
        await self.db.commit()

    async def list_issue_clocks(
        self, *, workspace_id: str, issue_id: str
    ) -> list[tuple[IssueSlaClock, Optional[str]]]:
        issue_q = await self.db.execute(
            select(Issue).where(
                Issue.id == issue_id,
                Issue.workspace_id == workspace_id,
                Issue.is_deleted == False,  # noqa: E712
            )
        )
        issue = issue_q.scalar_one_or_none()
        if not issue:
            raise HTTPException(status_code=404, detail="Issue 不存在")
        q = await self.db.execute(
            select(IssueSlaClock, SlaPolicy.name)
            .outerjoin(SlaPolicy, SlaPolicy.id == IssueSlaClock.policy_id)
            .where(
                IssueSlaClock.issue_id == issue_id,
                IssueSlaClock.workspace_id == workspace_id,
            )
            .order_by(IssueSlaClock.started_at.desc())
        )
        return [(c, name) for c, name in q.all()]

    async def sync_clocks(
        self,
        *,
        issue: Issue,
        old_status: Optional[str],
        new_status: Optional[str],
    ) -> None:
        """Start/stop clocks for enabled time_in_status policies. Same txn as caller."""
        if new_status is None:
            return
        new_s = _status_str(new_status)
        old_s = _status_str(old_status) if old_status is not None else None
        if old_s is not None and old_s == new_s:
            return
        if not issue.workspace_id:
            return

        pq = await self.db.execute(
            select(SlaPolicy).where(
                SlaPolicy.workspace_id == issue.workspace_id,
                SlaPolicy.enabled == True,  # noqa: E712
                SlaPolicy.metric == "time_in_status",
            )
        )
        policies = list(pq.scalars().all())
        if not policies:
            return

        now = datetime.utcnow()
        for policy in policies:
            starts = list(policy.start_statuses or [])
            # stop running first if stop condition met
            rq = await self.db.execute(
                select(IssueSlaClock).where(
                    IssueSlaClock.issue_id == issue.id,
                    IssueSlaClock.policy_id == policy.id,
                    IssueSlaClock.status == "running",
                )
            )
            running = rq.scalar_one_or_none()
            if running and _should_stop(policy, new_s):
                running.status = "met"
                running.stopped_at = now
                continue

            if new_s in starts:
                # ensure no double running
                if running is None:
                    # re-check in case we didn't load (shouldn't)
                    rq2 = await self.db.execute(
                        select(IssueSlaClock).where(
                            IssueSlaClock.issue_id == issue.id,
                            IssueSlaClock.policy_id == policy.id,
                            IssueSlaClock.status == "running",
                        )
                    )
                    if rq2.scalar_one_or_none() is None:
                        clock = IssueSlaClock(
                            workspace_id=issue.workspace_id,
                            issue_id=issue.id,
                            policy_id=policy.id,
                            status="running",
                            started_at=now,
                            deadline_at=now + timedelta(minutes=int(policy.target_minutes)),
                            start_status=new_s,
                        )
                        self.db.add(clock)

    async def run_due(
        self,
        *,
        workspace_id: str,
        actor_user_id: Optional[str] = None,
        now: Optional[datetime] = None,
    ) -> dict:
        now = now or datetime.utcnow()
        q = await self.db.execute(
            select(IssueSlaClock, SlaPolicy)
            .join(SlaPolicy, SlaPolicy.id == IssueSlaClock.policy_id)
            .where(
                IssueSlaClock.workspace_id == workspace_id,
                IssueSlaClock.status == "running",
                IssueSlaClock.deadline_at <= now,
            )
        )
        rows = list(q.all())
        scanned = len(rows)
        breached = 0
        notifications_created = 0
        skipped = 0
        errors: list[dict] = []

        for clock, policy in rows:
            try:
                if not policy.enabled:
                    skipped += 1
                    continue
                # idempotent: only running reaches here
                clock.status = "breached"
                clock.breached_at = now
                await self.db.flush()
                breached += 1

                issue_q = await self.db.execute(
                    select(Issue).where(
                        Issue.id == clock.issue_id,
                        Issue.workspace_id == workspace_id,
                    )
                )
                issue = issue_q.scalar_one_or_none()
                if not issue:
                    skipped += 1
                    continue

                recipients: list[str] = []
                if policy.notify_assignee and issue.assignee_id:
                    recipients.append(str(issue.assignee_id))
                if policy.notify_watchers:
                    wq = await self.db.execute(
                        select(IssueWatcher.user_id).where(
                            IssueWatcher.issue_id == issue.id
                        )
                    )
                    for uid in wq.scalars().all():
                        recipients.append(str(uid))
                # dedupe
                seen: set[str] = set()
                uniq: list[str] = []
                for uid in recipients:
                    if uid not in seen:
                        seen.add(uid)
                        uniq.append(uid)

                title = f"SLA 违约 {issue.issue_code} · {policy.name}"
                body = (
                    f"started={clock.started_at.isoformat() if clock.started_at else ''} "
                    f"deadline={clock.deadline_at.isoformat() if clock.deadline_at else ''}"
                )
                notif_svc = NotificationService(self.db)
                for uid in uniq:
                    n = await notif_svc.create(
                        workspace_id=workspace_id,
                        recipient_user_id=uid,
                        actor_user_id=None,  # avoid self-skip; tick has no actor meaning
                        type="sla_breached",
                        resource_type="issue",
                        resource_id=str(issue.id),
                        title=title,
                        body=body,
                    )
                    if n is not None:
                        notifications_created += 1

                try:
                    await fire_webhooks(
                        self.db,
                        workspace_id=workspace_id,
                        event_type="issue.sla_breached",
                        data={
                            "id": str(issue.id),
                            "issueCode": issue.issue_code,
                            "title": issue.title,
                            "policyId": policy.id,
                            "policyName": policy.name,
                            "deadlineAt": clock.deadline_at.isoformat()
                            if clock.deadline_at
                            else None,
                            "breachedAt": clock.breached_at.isoformat()
                            if clock.breached_at
                            else None,
                            "actorUserId": None,
                        },
                    )
                except Exception as wh_err:  # noqa: BLE001
                    logger.exception("sla webhook failed: %s", wh_err)

                await self.db.commit()
            except Exception as e:  # noqa: BLE001
                logger.exception("sla run-due clock %s failed", clock.id)
                await self.db.rollback()
                errors.append({"clockId": clock.id, "message": str(e)})

        return {
            "scanned": scanned,
            "breached": breached,
            "notificationsCreated": notifications_created,
            "skipped": skipped,
            "errors": errors,
        }
