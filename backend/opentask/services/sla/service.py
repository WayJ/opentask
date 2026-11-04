"""SLA policies + clocks + run-due (E42/E45/E48) + business hours (E50)."""
from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any, Optional

from fastapi import HTTPException, status as http_status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from opentask.models.issue.enums import IssueStatus, TimelineAction
from opentask.models.issue.model import Issue, IssueTimeline
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
from opentask.models.workspace.model import Workspace, WorkspaceMember
from opentask.services.sla.business_hours import (
    add_business_minutes,
    elapsed_business_minutes,
    is_business_hours_enabled,
    normalize_windows,
)
from opentask.services.notification.service import NotificationService
from opentask.services.automation.service import fire_automations
from opentask.services.workspace_webhook.service import fire_webhooks

logger = logging.getLogger(__name__)

RECOMPUTE_CAP = 500


def _wall_deadline(now: datetime, minutes: int) -> datetime:
    return now + timedelta(minutes=int(minutes))


def _wall_elapsed(start: datetime, end: datetime) -> int:
    return max(0, int((end - start).total_seconds() // 60))


def compute_deadline(now: datetime, minutes: int, ws: Workspace | None) -> datetime:
    if ws is not None and is_business_hours_enabled(ws.timezone, ws.business_hours):
        windows = normalize_windows((ws.business_hours or {}).get("windows"))
        return add_business_minutes(now, int(minutes), str(ws.timezone), windows)
    return _wall_deadline(now, minutes)


def compute_elapsed(start: datetime, end: datetime, ws: Workspace | None) -> int:
    if ws is not None and is_business_hours_enabled(ws.timezone, ws.business_hours):
        windows = normalize_windows((ws.business_hours or {}).get("windows"))
        return elapsed_business_minutes(start, end, str(ws.timezone), windows)
    return _wall_elapsed(start, end)


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
        "pauseStatuses": list(row.pause_statuses or []),
        "targetMinutes": int(row.target_minutes),
        "notifyAssignee": bool(row.notify_assignee),
        "notifyWatchers": bool(row.notify_watchers),
        "createdAt": row.created_at.isoformat() if row.created_at else None,
        "updatedAt": row.updated_at.isoformat() if row.updated_at else None,
    }


def serialize_clock(
    row: IssueSlaClock,
    *,
    policy_name: Optional[str] = None,
    metric: Optional[str] = None,
) -> dict:
    return {
        "id": row.id,
        "workspaceId": row.workspace_id,
        "issueId": row.issue_id,
        "policyId": row.policy_id,
        "policyName": policy_name,
        "metric": metric,
        "status": row.status,
        "startedAt": row.started_at.isoformat() if row.started_at else None,
        "deadlineAt": row.deadline_at.isoformat() if row.deadline_at else None,
        "stoppedAt": row.stopped_at.isoformat() if row.stopped_at else None,
        "breachedAt": row.breached_at.isoformat() if row.breached_at else None,
        "startStatus": row.start_status,
        "elapsedBeforePauseMinutes": int(row.elapsed_before_pause_minutes or 0),
        "pausedAt": row.paused_at.isoformat() if row.paused_at else None,
        "segmentStartedAt": row.segment_started_at.isoformat() if row.segment_started_at else None,
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
        pause_statuses: Optional[list[str]] = None,
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
        pauses = _validate_statuses(pause_statuses or [], field="pauseStatuses", allow_empty=True)
        minutes = _validate_target(target_minutes)
        row = SlaPolicy(
            workspace_id=workspace_id,
            name=name,
            enabled=bool(enabled),
            metric=metric,
            start_statuses=starts,
            stop_statuses=stops,
            pause_statuses=pauses,
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
        if "pauseStatuses" in updates and updates["pauseStatuses"] is not None:
            row.pause_statuses = _validate_statuses(
                updates["pauseStatuses"], field="pauseStatuses", allow_empty=True
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
    ) -> list[tuple[IssueSlaClock, Optional[str], Optional[str]]]:
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
            select(IssueSlaClock, SlaPolicy.name, SlaPolicy.metric)
            .outerjoin(SlaPolicy, SlaPolicy.id == IssueSlaClock.policy_id)
            .where(
                IssueSlaClock.issue_id == issue_id,
                IssueSlaClock.workspace_id == workspace_id,
            )
            .order_by(IssueSlaClock.started_at.desc())
        )
        return [(c, name, metric) for c, name, metric in q.all()]

    async def sync_clocks(
        self,
        *,
        issue: Issue,
        old_status: Optional[str],
        new_status: Optional[str],
    ) -> None:
        """Start/pause/resume/stop clocks. Same txn as caller. Priority: stop > pause > start."""
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
            )
        )
        policies = list(pq.scalars().all())
        if not policies:
            return

        wq = await self.db.execute(
            select(Workspace).where(Workspace.id == issue.workspace_id)
        )
        ws = wq.scalar_one_or_none()

        now = datetime.utcnow()
        for policy in policies:
            starts = list(policy.start_statuses or [])
            pauses = list(policy.pause_statuses or [])

            aq = await self.db.execute(
                select(IssueSlaClock).where(
                    IssueSlaClock.issue_id == issue.id,
                    IssueSlaClock.policy_id == policy.id,
                    IssueSlaClock.status.in_(("running", "paused")),
                )
            )
            active = aq.scalar_one_or_none()

            # 1) stop wins (running or paused)
            if active is not None and _should_stop(policy, new_s):
                active.status = "met"
                active.stopped_at = now
                continue

            # 2) running → pause
            if active is not None and active.status == "running" and new_s in pauses:
                seg = active.segment_started_at or active.started_at
                if seg is not None:
                    delta_min = compute_elapsed(seg, now, ws)
                    active.elapsed_before_pause_minutes = int(
                        active.elapsed_before_pause_minutes or 0
                    ) + delta_min
                active.status = "paused"
                active.paused_at = now
                # Q3: keep old deadline_at
                # E48: pause timeline only — no webhook/automation (Q3a)
                self.db.add(
                    IssueTimeline(
                        issue_id=issue.id,
                        user_id=None,
                        action_type=TimelineAction.SLA_PAUSED,
                        action_data={
                            "policyId": policy.id,
                            "policyName": policy.name,
                            "metric": policy.metric,
                            "elapsedBeforePauseMinutes": int(
                                active.elapsed_before_pause_minutes or 0
                            ),
                            "fromStatus": old_s,
                            "toStatus": new_s,
                        },
                    )
                )
                continue

            # 3) paused → resume (not stop, not still in pause)
            if (
                active is not None
                and active.status == "paused"
                and new_s not in pauses
            ):
                elapsed = int(active.elapsed_before_pause_minutes or 0)
                remaining = max(0, int(policy.target_minutes) - elapsed)
                active.status = "running"
                active.paused_at = None
                active.segment_started_at = now
                active.deadline_at = compute_deadline(now, remaining, ws)
                self.db.add(
                    IssueTimeline(
                        issue_id=issue.id,
                        user_id=None,
                        action_type=TimelineAction.SLA_RESUMED,
                        action_data={
                            "policyId": policy.id,
                            "policyName": policy.name,
                            "metric": policy.metric,
                            "remainingMinutes": remaining,
                            "newDeadlineAt": active.deadline_at.isoformat()
                            if active.deadline_at
                            else None,
                            "fromStatus": old_s,
                            "toStatus": new_s,
                        },
                    )
                )
                continue

            # 4) start new running if no active clock
            if new_s in starts and active is None:
                clock = IssueSlaClock(
                    workspace_id=issue.workspace_id,
                    issue_id=issue.id,
                    policy_id=policy.id,
                    status="running",
                    started_at=now,
                    deadline_at=compute_deadline(now, int(policy.target_minutes), ws),
                    start_status=new_s,
                    elapsed_before_pause_minutes=0,
                    paused_at=None,
                    segment_started_at=now,
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
                            "metric": policy.metric,
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

                try:
                    await fire_automations(
                        self.db,
                        workspace_id=workspace_id,
                        trigger_type="issue.sla_breached",
                        issue=issue,
                        actor_user_id=None,
                        event={
                            "policyId": policy.id,
                            "policyName": policy.name,
                            "metric": policy.metric,
                            "deadlineAt": clock.deadline_at.isoformat()
                            if clock.deadline_at
                            else None,
                            "breachedAt": clock.breached_at.isoformat()
                            if clock.breached_at
                            else None,
                            "clockId": clock.id,
                        },
                    )
                except Exception as auto_err:  # noqa: BLE001
                    logger.exception("sla automation failed: %s", auto_err)
                    errors.append(
                        {"clockId": clock.id, "message": f"automation: {auto_err}"}
                    )

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


    async def recompute_deadlines_for_workspace(
        self,
        *,
        workspace_id: str,
        cap: int = RECOMPUTE_CAP,
    ) -> dict:
        """Batch-recompute running/paused deadline_at after business-hours config change."""
        wq = await self.db.execute(select(Workspace).where(Workspace.id == workspace_id))
        ws = wq.scalar_one_or_none()
        if ws is None:
            return {"recomputed": 0, "scanned": 0, "capped": False}

        q = await self.db.execute(
            select(IssueSlaClock, SlaPolicy)
            .join(SlaPolicy, SlaPolicy.id == IssueSlaClock.policy_id)
            .where(
                IssueSlaClock.workspace_id == workspace_id,
                IssueSlaClock.status.in_(("running", "paused")),
            )
            .order_by(IssueSlaClock.started_at.asc())
            .limit(int(cap) + 1)
        )
        rows = list(q.all())
        capped = len(rows) > cap
        if capped:
            logger.warning(
                "sla business-hours recompute capped at %s for workspace %s",
                cap,
                workspace_id,
            )
            rows = rows[:cap]

        now = datetime.utcnow()
        recomputed = 0
        for clock, policy in rows:
            if clock.status == "paused":
                elapsed = int(clock.elapsed_before_pause_minutes or 0)
            else:
                seg = clock.segment_started_at or clock.started_at or now
                elapsed = int(clock.elapsed_before_pause_minutes or 0) + compute_elapsed(
                    seg, now, ws
                )
            remaining = max(0, int(policy.target_minutes) - elapsed)
            clock.deadline_at = compute_deadline(now, remaining, ws)
            recomputed += 1
        return {"recomputed": recomputed, "scanned": recomputed, "capped": capped}

    async def mark_first_response(
        self,
        *,
        issue: Issue,
        actor_user_id: str,
    ) -> None:
        """Mark first_response clocks met on first non-creator comment (Q1a/Q2b). Same txn."""
        if not issue or not issue.workspace_id or not actor_user_id:
            return
        creator = issue.created_by or issue.reporter_id
        if creator and str(actor_user_id) == str(creator):
            return

        pq = await self.db.execute(
            select(SlaPolicy).where(
                SlaPolicy.workspace_id == issue.workspace_id,
                SlaPolicy.enabled == True,  # noqa: E712
                SlaPolicy.metric == "first_response",
            )
        )
        policies = list(pq.scalars().all())
        if not policies:
            return

        now = datetime.utcnow()
        for policy in policies:
            aq = await self.db.execute(
                select(IssueSlaClock).where(
                    IssueSlaClock.issue_id == issue.id,
                    IssueSlaClock.policy_id == policy.id,
                    IssueSlaClock.status.in_(("running", "paused")),
                )
            )
            active = aq.scalar_one_or_none()
            if active is None:
                continue
            active.status = "met"
            active.stopped_at = now
            # responseKind/actorId recorded conceptually on met; no pause-class timeline (D4)
