"""Issue recurrence CRUD + run-due tick (E35)."""
from __future__ import annotations

import calendar
import logging
from datetime import date, datetime, timedelta
from typing import Any, Optional

from fastapi import HTTPException, status as http_status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from opentask.models.custom_field.model import CustomField
from opentask.models.issue.enums import IssuePriority, IssueType
from opentask.models.issue.model import IssueTag
from opentask.models.issue.schema import IssueCreate
from opentask.models.issue_recurrence.model import RECURRENCE_INTERVALS, IssueRecurrence
from opentask.models.tag.model import Tag
from opentask.models.workspace.model import Workspace, WorkspaceMember
from opentask.services.workspace_time import local_today
from opentask.services.custom_field.service import CustomFieldService, validate_value
from opentask.services.issue_service import IssueService

logger = logging.getLogger(__name__)


def require_writer(member: WorkspaceMember) -> None:
    if member.role not in ("owner", "member"):
        raise HTTPException(
            status_code=http_status.HTTP_403_FORBIDDEN,
            detail="仅 member/owner 可写",
        )


def serialize_recurrence(row: IssueRecurrence) -> dict:
    return {
        "id": row.id,
        "workspaceId": row.workspace_id,
        "titleTemplate": row.title_template,
        "description": row.description,
        "priority": row.priority,
        "labels": list(row.labels_json or []),
        "projectId": row.project_id,
        "assigneeId": row.assignee_id,
        "customFields": dict(row.custom_fields_json or {}),
        "interval": row.interval,
        "weekday": row.weekday,
        "monthday": row.monthday,
        "nextRunAt": row.next_run_at.isoformat() if row.next_run_at else None,
        "enabled": bool(row.enabled),
        "lastIssueId": row.last_issue_id,
        "createdBy": row.created_by,
        "createdAt": row.created_at.isoformat() if row.created_at else None,
        "updatedAt": row.updated_at.isoformat() if row.updated_at else None,
    }


def _parse_dt(value: Any) -> datetime:
    if isinstance(value, datetime):
        return value.replace(tzinfo=None) if value.tzinfo else value
    if isinstance(value, str):
        s = value.strip().replace("Z", "")
        if "+" in s[10:]:
            s = s.split("+")[0]
        return datetime.fromisoformat(s)
    raise HTTPException(status_code=400, detail="nextRunAt 无效")


def expand_title(
    template: str, when: datetime, *, local_date: date | None = None
) -> str:
    d = local_date if local_date is not None else when.date()
    date_s = d.strftime("%Y-%m-%d")
    return (
        (template or "")
        .replace("{yyyy-mm-dd}", date_s)
        .replace("{date}", date_s)
    )


def add_months(dt: datetime, months: int = 1) -> datetime:
    y = dt.year + (dt.month - 1 + months) // 12
    m = (dt.month - 1 + months) % 12 + 1
    last = calendar.monthrange(y, m)[1]
    d = min(dt.day, last)
    return dt.replace(year=y, month=m, day=d)


def snap_weekday(dt: datetime, weekday: int) -> datetime:
    """Move forward to target weekday (0=Mon..6=Sun); same day if already."""
    cur = dt.weekday()  # Mon=0
    delta = (weekday - cur) % 7
    return dt + timedelta(days=delta)


def snap_monthday(dt: datetime, monthday: int) -> datetime:
    last = calendar.monthrange(dt.year, dt.month)[1]
    d = min(max(1, monthday), last)
    return dt.replace(day=d)


def advance_once(dt: datetime, interval: str, weekday: int | None, monthday: int | None) -> datetime:
    if interval == "daily":
        return dt + timedelta(days=1)
    if interval == "weekly":
        nxt = dt + timedelta(days=7)
        if weekday is not None:
            # keep weekday alignment
            return snap_weekday(nxt.replace(hour=dt.hour, minute=dt.minute, second=dt.second, microsecond=dt.microsecond), weekday)
        return nxt
    if interval == "monthly":
        nxt = add_months(dt, 1)
        if monthday is not None:
            return snap_monthday(nxt, monthday)
        return nxt
    raise ValueError(f"unknown interval {interval}")


def advance_until_future(
    start: datetime,
    *,
    now: datetime,
    interval: str,
    weekday: int | None,
    monthday: int | None,
) -> datetime:
    nxt = advance_once(start, interval, weekday, monthday)
    # safety cap
    for _ in range(4000):
        if nxt > now:
            return nxt
        nxt = advance_once(nxt, interval, weekday, monthday)
    return nxt


class IssueRecurrenceService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list(self, *, workspace_id: str) -> list[IssueRecurrence]:
        stmt = (
            select(IssueRecurrence)
            .where(IssueRecurrence.workspace_id == workspace_id)
            .order_by(IssueRecurrence.next_run_at.asc(), IssueRecurrence.created_at.asc())
        )
        return list((await self.db.execute(stmt)).scalars().all())

    async def get(self, *, workspace_id: str, recurrence_id: str) -> IssueRecurrence:
        return await self._get_or_404(workspace_id, recurrence_id)

    async def create(
        self,
        *,
        workspace_id: str,
        user_id: str,
        title_template: str,
        interval: str,
        next_run_at: Any,
        description: str | None = None,
        priority: str | None = None,
        labels: list[str] | None = None,
        project_id: str | None = None,
        assignee_id: str | None = None,
        custom_fields: dict | None = None,
        weekday: int | None = None,
        monthday: int | None = None,
        enabled: bool = True,
    ) -> IssueRecurrence:
        self._validate_interval(interval, weekday, monthday)
        if priority is not None:
            self._validate_priority(priority)
        title = (title_template or "").strip()
        if not title:
            raise HTTPException(status_code=400, detail="titleTemplate 必填")
        nxt = _parse_dt(next_run_at)
        row = IssueRecurrence(
            workspace_id=workspace_id,
            title_template=title,
            description=description,
            priority=priority,
            labels_json=list(labels or []),
            project_id=project_id,
            assignee_id=assignee_id,
            custom_fields_json=dict(custom_fields or {}),
            interval=interval,
            weekday=weekday,
            monthday=monthday,
            next_run_at=nxt,
            enabled=enabled,
            created_by=user_id,
        )
        self.db.add(row)
        await self.db.commit()
        await self.db.refresh(row)
        return row

    async def update(
        self,
        *,
        workspace_id: str,
        recurrence_id: str,
        title_template: str | None = None,
        description: str | None = None,
        clear_description: bool = False,
        priority: str | None = None,
        set_priority: bool = False,
        labels: list[str] | None = None,
        project_id: str | None = None,
        set_project_id: bool = False,
        assignee_id: str | None = None,
        set_assignee_id: bool = False,
        custom_fields: dict | None = None,
        interval: str | None = None,
        weekday: int | None = None,
        set_weekday: bool = False,
        monthday: int | None = None,
        set_monthday: bool = False,
        next_run_at: Any = None,
        enabled: bool | None = None,
    ) -> IssueRecurrence:
        row = await self._get_or_404(workspace_id, recurrence_id)
        if title_template is not None:
            t = title_template.strip()
            if not t:
                raise HTTPException(status_code=400, detail="titleTemplate 必填")
            row.title_template = t
        if clear_description:
            row.description = None
        elif description is not None:
            row.description = description
        if set_priority:
            if priority is not None:
                self._validate_priority(priority)
            row.priority = priority
        if labels is not None:
            row.labels_json = list(labels)
        if set_project_id:
            row.project_id = project_id
        if set_assignee_id:
            row.assignee_id = assignee_id
        if custom_fields is not None:
            row.custom_fields_json = dict(custom_fields)
        if interval is not None:
            row.interval = interval
        if set_weekday:
            row.weekday = weekday
        if set_monthday:
            row.monthday = monthday
        self._validate_interval(row.interval, row.weekday, row.monthday)
        if next_run_at is not None:
            row.next_run_at = _parse_dt(next_run_at)
        if enabled is not None:
            row.enabled = enabled
        row.updated_at = datetime.utcnow()
        await self.db.commit()
        await self.db.refresh(row)
        return row

    async def delete(self, *, workspace_id: str, recurrence_id: str) -> None:
        row = await self._get_or_404(workspace_id, recurrence_id)
        await self.db.delete(row)
        await self.db.commit()

    async def run_due(
        self,
        *,
        workspace_id: str,
        actor_user_id: str,
        now: datetime | None = None,
    ) -> dict[str, Any]:
        now = now or datetime.utcnow()
        stmt = (
            select(IssueRecurrence)
            .where(
                IssueRecurrence.workspace_id == workspace_id,
                IssueRecurrence.enabled.is_(True),
                IssueRecurrence.next_run_at <= now,
            )
            .order_by(IssueRecurrence.next_run_at.asc())
        )
        rows = list((await self.db.execute(stmt)).scalars().all())
        created = 0
        errors: list[dict[str, str]] = []
        issues: list[dict[str, str]] = []

        for row in rows:
            try:
                issue_info = await self._spawn_one(row, actor_user_id=actor_user_id, now=now)
                created += 1
                issues.append(issue_info)
                row.last_issue_id = issue_info["id"]
                row.next_run_at = advance_until_future(
                    row.next_run_at,
                    now=now,
                    interval=row.interval,
                    weekday=row.weekday,
                    monthday=row.monthday,
                )
                row.updated_at = datetime.utcnow()
                await self.db.commit()
            except Exception as exc:  # noqa: BLE001 — per-row isolation
                await self.db.rollback()
                msg = str(exc)
                logger.exception("recurrence %s run failed: %s", row.id, msg)
                errors.append({"recurrenceId": row.id, "message": msg})
                # still try to advance so we don't tight-loop on poison rows
                try:
                    fresh = await self._get_or_404(workspace_id, row.id)
                    fresh.next_run_at = advance_until_future(
                        fresh.next_run_at,
                        now=now,
                        interval=fresh.interval,
                        weekday=fresh.weekday,
                        monthday=fresh.monthday,
                    )
                    fresh.updated_at = datetime.utcnow()
                    await self.db.commit()
                except Exception:  # noqa: BLE001
                    await self.db.rollback()
                    logger.exception("failed to advance poison recurrence %s", row.id)

        return {"created": created, "errors": errors, "issues": issues}

    async def _spawn_one(
        self, row: IssueRecurrence, *, actor_user_id: str, now: datetime
    ) -> dict[str, str]:
        actor = row.created_by or actor_user_id
        ws_row = (
            await self.db.execute(
                select(Workspace).where(Workspace.id == row.workspace_id)
            )
        ).scalar_one_or_none()
        title = expand_title(
            row.title_template,
            now,
            local_date=local_today(ws_row, now_utc=now),
        )
        priority = IssuePriority.MEDIUM
        if row.priority:
            self._validate_priority(row.priority)
            priority = IssuePriority(row.priority)

        if row.assignee_id:
            await self._assert_member(workspace_id=row.workspace_id, user_id=row.assignee_id)
        if row.project_id:
            await self._assert_project(workspace_id=row.workspace_id, project_id=row.project_id)

        issue_svc = IssueService(self.db)
        issue = await issue_svc.create_issue(
            IssueCreate(
                title=title,
                description=row.description,
                type=IssueType.FEATURE,
                priority=priority,
                assignee_id=row.assignee_id,
                project_id=row.project_id,
            ),
            user_id=actor,
            workspace_id=row.workspace_id,
        )

        label_errors: list[str] = []
        for name in row.labels_json or []:
            tag = (
                await self.db.execute(
                    select(Tag).where(
                        Tag.workspace_id == row.workspace_id,
                        Tag.name == str(name),
                    )
                )
            ).scalar_one_or_none()
            if not tag:
                label_errors.append(f"label:{name}")
                continue
            exists = (
                await self.db.execute(
                    select(IssueTag).where(
                        IssueTag.issue_id == issue.id, IssueTag.tag_id == tag.id
                    )
                )
            ).scalar_one_or_none()
            if not exists:
                self.db.add(IssueTag(issue_id=issue.id, tag_id=tag.id))

        cf_errors: list[str] = []
        cf_map = dict(row.custom_fields_json or {})
        if cf_map:
            entries = []
            for key, value in cf_map.items():
                cf = (
                    await self.db.execute(
                        select(CustomField).where(
                            CustomField.workspace_id == row.workspace_id,
                            CustomField.key == str(key),
                            CustomField.archived_at.is_(None),
                        )
                    )
                ).scalar_one_or_none()
                if not cf:
                    cf_errors.append(f"cf:{key}:unknown")
                    continue
                try:
                    normalized = validate_value(cf, value)
                    entries.append({"fieldId": cf.id, "value": normalized})
                except Exception as ve:  # noqa: BLE001
                    cf_errors.append(f"cf:{key}:{ve}")
            if entries:
                await CustomFieldService(self.db).upsert_issue_values(
                    workspace_id=row.workspace_id,
                    issue_id=str(issue.id),
                    entries=entries,
                )

        await self.db.commit()
        await self.db.refresh(issue)

        if label_errors or cf_errors:
            logger.warning(
                "recurrence %s partial attach: labels=%s cf=%s",
                row.id,
                label_errors,
                cf_errors,
            )

        return {
            "id": str(issue.id),
            "issueCode": issue.issue_code,
            "recurrenceId": row.id,
            "title": issue.title,
        }

    async def _assert_member(self, *, workspace_id: str, user_id: str) -> None:
        m = (
            await self.db.execute(
                select(WorkspaceMember).where(
                    WorkspaceMember.workspace_id == workspace_id,
                    WorkspaceMember.user_id == user_id,
                )
            )
        ).scalar_one_or_none()
        if not m:
            raise HTTPException(status_code=400, detail="assignee 非本工作区成员")

    async def _assert_project(self, *, workspace_id: str, project_id: str) -> None:
        from opentask.models.requirement.model import Requirement

        # Project may be modeled as Requirement/project — soft check via IssueService validation
        # Prefer lightweight existence if Requirement has workspace_id
        try:
            row = (
                await self.db.execute(
                    select(Requirement).where(Requirement.id == project_id)
                )
            ).scalar_one_or_none()
        except Exception:  # noqa: BLE001
            row = None
        if row is None:
            # Fall through: IssueService.create will validate project_id
            return
        ws = getattr(row, "workspace_id", None)
        if ws is not None and str(ws) != str(workspace_id):
            raise HTTPException(status_code=400, detail="project 不属于本工作区")

    async def _get_or_404(self, workspace_id: str, recurrence_id: str) -> IssueRecurrence:
        stmt = select(IssueRecurrence).where(
            IssueRecurrence.id == recurrence_id,
            IssueRecurrence.workspace_id == workspace_id,
        )
        row = (await self.db.execute(stmt)).scalar_one_or_none()
        if not row:
            raise HTTPException(status_code=404, detail="周期规则不存在")
        return row

    @staticmethod
    def _validate_interval(interval: str, weekday: int | None, monthday: int | None) -> None:
        if interval not in RECURRENCE_INTERVALS:
            raise HTTPException(
                status_code=400,
                detail=f"interval 须为 {', '.join(RECURRENCE_INTERVALS)}",
            )
        if weekday is not None and (weekday < 0 or weekday > 6):
            raise HTTPException(status_code=400, detail="weekday 须为 0–6（周一=0）")
        if monthday is not None and (monthday < 1 or monthday > 31):
            raise HTTPException(status_code=400, detail="monthday 须为 1–31")

    @staticmethod
    def _validate_priority(priority: str) -> None:
        allowed = {p.value for p in IssuePriority}
        if priority not in allowed:
            raise HTTPException(
                status_code=400,
                detail=f"priority 无效，允许: {', '.join(sorted(allowed))}",
            )
