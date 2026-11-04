"""Workspace Insights 只读聚合（E24 + E55 + E59 + E61 shared reports）。"""
from __future__ import annotations

import csv
import io
import uuid
from datetime import date, datetime, timedelta
from typing import Any, Optional

from fastapi import HTTPException, status as http_status
from sqlalchemy import case, exists, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from opentask.models.cycle.model import Cycle
from opentask.models.insights_digest_delivery.model import InsightsDigestDelivery
from opentask.models.insights_saved_report.model import InsightsSavedReport
from opentask.models.issue.model import Issue, IssueTag
from opentask.models.notification_preference.model import NotificationPreference
from opentask.models.requirement.model import Project
from opentask.models.tag.model import Tag
from opentask.models.user.model import UserModel

DONE_STATUSES = frozenset({"resolved", "closed"})
DEFAULT_ASSIGNEE_LIMIT = 10
TREND_DAYS = 14
VELOCITY_DAYS = 14
REPORT_CAP = 20  # personal per user per WS (E59/E61)
SHARED_REPORT_CAP = 50  # workspace-visibility per WS (E61 Q6a)
VIS_PERSONAL = "personal"
VIS_WORKSPACE = "workspace"
WRITER_ROLES = frozenset({"owner", "member"})


def normalize_visibility(raw: Optional[str], *, default: str = VIS_PERSONAL) -> str:
    if raw is None or str(raw).strip() == "":
        return default
    v = str(raw).strip().lower()
    if v not in (VIS_PERSONAL, VIS_WORKSPACE):
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail="visibility 须为 personal 或 workspace",
        )
    return v



def normalize_label_ids(
    *,
    label_id: Optional[int] = None,
    label_ids: Optional[list[int]] = None,
) -> Optional[list[int]]:
    """Merge alias → list; empty → None. Caller must reject labelId+labelIds conflict."""
    if label_ids is not None:
        seen: set[int] = set()
        out: list[int] = []
        for raw in label_ids:
            try:
                n = int(raw)
            except (TypeError, ValueError):
                continue
            if n not in seen:
                seen.add(n)
                out.append(n)
        return out or None
    if label_id is not None:
        return [int(label_id)]
    return None


def parse_label_ids_query(
    *,
    label_id: Optional[int],
    label_ids_raw: Optional[list[str]],
) -> Optional[list[int]]:
    """Q1a: repeated query + comma string; labelId+labelIds → 400."""
    parsed: list[int] = []
    if label_ids_raw:
        for item in label_ids_raw:
            for part in str(item).split(","):
                part = part.strip()
                if not part:
                    continue
                try:
                    parsed.append(int(part))
                except ValueError as exc:
                    raise HTTPException(
                        status_code=http_status.HTTP_400_BAD_REQUEST,
                        detail="labelIds 非法",
                    ) from exc
    if label_id is not None and parsed:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail="labelId 与 labelIds 不可同时传入",
        )
    if parsed:
        return normalize_label_ids(label_ids=parsed)
    if label_id is not None:
        return [int(label_id)]
    return None


def serialize_saved_report(
    row: InsightsSavedReport, *, viewer_user_id: Optional[str] = None
) -> dict[str, Any]:
    owner = str(row.owner_user_id)
    viewer = str(viewer_user_id) if viewer_user_id is not None else owner
    return {
        "id": row.id,
        "workspaceId": row.workspace_id,
        "ownerUserId": owner,
        "name": row.name,
        "filters": dict(row.filters or {}),
        "isDefault": bool(row.is_default),
        "visibility": getattr(row, "visibility", None) or VIS_PERSONAL,
        "canEdit": owner == viewer,
        "createdAt": row.created_at.isoformat() if row.created_at else None,
        "updatedAt": row.updated_at.isoformat() if row.updated_at else None,
    }


class InsightsService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def summary(
        self,
        *,
        workspace_id: str,
        cycle_id: Optional[str] = None,
        assignee_limit: int = DEFAULT_ASSIGNEE_LIMIT,
        project_id: Optional[str] = None,
        label_id: Optional[int] = None,
        label_ids: Optional[list[int]] = None,
    ) -> dict[str, Any]:
        ids = normalize_label_ids(label_id=label_id, label_ids=label_ids)
        await self._ensure_filters(workspace_id, project_id=project_id, label_ids=ids)
        limit = max(1, min(int(assignee_limit or DEFAULT_ASSIGNEE_LIMIT), 100))
        status_counts = await self._status_counts(
            workspace_id, project_id=project_id, label_ids=ids
        )
        priority_counts = await self._priority_counts(
            workspace_id, project_id=project_id, label_ids=ids
        )
        assignee_counts = await self._assignee_counts(
            workspace_id, limit=limit, project_id=project_id, label_ids=ids
        )
        cycle_snapshot = await self._cycle_snapshot(
            workspace_id, cycle_id=cycle_id, project_id=project_id, label_ids=ids
        )
        created_vs_completed = await self._created_vs_completed(
            workspace_id, days=TREND_DAYS, project_id=project_id, label_ids=ids
        )
        estimate_velocity = await self._estimate_velocity(
            workspace_id, days=VELOCITY_DAYS, project_id=project_id, label_ids=ids
        )
        return {
            "statusCounts": status_counts,
            "priorityCounts": priority_counts,
            "assigneeCounts": assignee_counts,
            "cycleSnapshot": cycle_snapshot,
            "createdVsCompleted": created_vs_completed,
            "estimateVelocity": estimate_velocity,
        }

    async def export_csv(
        self,
        *,
        workspace_id: str,
        cycle_id: Optional[str] = None,
        assignee_limit: int = DEFAULT_ASSIGNEE_LIMIT,
        project_id: Optional[str] = None,
        label_id: Optional[int] = None,
        label_ids: Optional[list[int]] = None,
    ) -> str:
        data = await self.summary(
            workspace_id=workspace_id,
            cycle_id=cycle_id,
            assignee_limit=assignee_limit,
            project_id=project_id,
            label_id=label_id,
            label_ids=label_ids,
        )
        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow(["kind", "key", "value"])
        for status, count in (data.get("statusCounts") or {}).items():
            writer.writerow(["status", status, int(count)])
        for priority, count in (data.get("priorityCounts") or {}).items():
            writer.writerow(["priority", priority, int(count)])
        for row in data.get("assigneeCounts") or []:
            key = row.get("assigneeId") if row.get("assigneeId") is not None else "unassigned"
            writer.writerow(["assignee", key, int(row.get("count") or 0)])
        vel = data.get("estimateVelocity") or {}
        for bucket in vel.get("buckets") or []:
            writer.writerow(
                [
                    "estimate_velocity",
                    bucket.get("date"),
                    float(bucket.get("completedPoints") or 0),
                ]
            )
        return buf.getvalue()

    # ------------------------------------------------------------------ reports

    async def list_reports(self, *, workspace_id: str, owner_user_id: str) -> list[dict]:
        """Q2a: mine (any visibility) ∪ workspace-shared in this WS."""
        uid = str(owner_user_id)
        result = await self.db.execute(
            select(InsightsSavedReport)
            .where(
                InsightsSavedReport.workspace_id == workspace_id,
                or_(
                    InsightsSavedReport.owner_user_id == uid,
                    InsightsSavedReport.visibility == VIS_WORKSPACE,
                ),
            )
            .order_by(InsightsSavedReport.updated_at.desc())
        )
        return [
            serialize_saved_report(r, viewer_user_id=uid) for r in result.scalars().all()
        ]

    async def create_report(
        self,
        *,
        workspace_id: str,
        owner_user_id: str,
        name: str,
        filters: Optional[dict] = None,
        is_default: bool = False,
        visibility: Optional[str] = None,
        actor_role: Optional[str] = None,
    ) -> dict:
        name = (name or "").strip()
        if not name:
            raise HTTPException(
                status_code=http_status.HTTP_400_BAD_REQUEST,
                detail="name 必填",
            )
        vis = normalize_visibility(visibility, default=VIS_PERSONAL)
        self._ensure_can_share(actor_role, vis)
        await self._ensure_cap(workspace_id, owner_user_id, vis)
        filters = self._normalize_filters(filters or {})
        await self._ensure_filter_refs(workspace_id, filters)
        if is_default:
            await self._clear_defaults(workspace_id, owner_user_id)
        row = InsightsSavedReport(
            id=str(uuid.uuid4()),
            workspace_id=workspace_id,
            owner_user_id=str(owner_user_id),
            name=name[:128],
            filters=filters,
            is_default=bool(is_default),
            visibility=vis,
        )
        self.db.add(row)
        await self.db.commit()
        await self.db.refresh(row)
        return serialize_saved_report(row, viewer_user_id=str(owner_user_id))

    async def update_report(
        self,
        *,
        workspace_id: str,
        owner_user_id: str,
        report_id: str,
        name: Optional[str] = None,
        filters: Optional[dict] = None,
        is_default: Optional[bool] = None,
        visibility: Optional[str] = None,
        actor_role: Optional[str] = None,
    ) -> dict:
        row = await self._get_own_report(workspace_id, owner_user_id, report_id)
        if name is not None:
            name = name.strip()
            if not name:
                raise HTTPException(
                    status_code=http_status.HTTP_400_BAD_REQUEST,
                    detail="name 不可为空",
                )
            row.name = name[:128]
        if filters is not None:
            filters = self._normalize_filters(filters)
            await self._ensure_filter_refs(workspace_id, filters)
            row.filters = filters
        if visibility is not None:
            new_vis = normalize_visibility(visibility)
            if new_vis != (row.visibility or VIS_PERSONAL):
                self._ensure_can_share(actor_role, new_vis)
                await self._ensure_cap(
                    workspace_id,
                    owner_user_id,
                    new_vis,
                    exclude_report_id=row.id,
                )
                row.visibility = new_vis
        if is_default is True:
            await self._clear_defaults(workspace_id, owner_user_id)
            row.is_default = True
        elif is_default is False:
            row.is_default = False
        row.updated_at = datetime.utcnow()
        await self.db.commit()
        await self.db.refresh(row)
        return serialize_saved_report(row, viewer_user_id=str(owner_user_id))

    async def delete_report(
        self, *, workspace_id: str, owner_user_id: str, report_id: str
    ) -> None:
        row = await self._get_own_report(workspace_id, owner_user_id, report_id)
        await self.db.delete(row)
        await self.db.commit()

    async def fork_report(
        self,
        *,
        workspace_id: str,
        owner_user_id: str,
        report_id: str,
        name: Optional[str] = None,
        actor_role: Optional[str] = None,
    ) -> dict:
        src = await self._get_readable_report(workspace_id, owner_user_id, report_id)
        fork_name = (name or "").strip() or f"副本 · {src.name}"
        return await self.create_report(
            workspace_id=workspace_id,
            owner_user_id=owner_user_id,
            name=fork_name[:128],
            filters=dict(src.filters or {}),
            is_default=False,
            visibility=VIS_PERSONAL,
            actor_role=actor_role,
        )

    async def _get_own_report(
        self, workspace_id: str, owner_user_id: str, report_id: str
    ) -> InsightsSavedReport:
        result = await self.db.execute(
            select(InsightsSavedReport).where(
                InsightsSavedReport.id == report_id,
                InsightsSavedReport.workspace_id == workspace_id,
                InsightsSavedReport.owner_user_id == str(owner_user_id),
            )
        )
        row = result.scalar_one_or_none()
        if row is None:
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail="报表不存在",
            )
        return row

    async def _get_readable_report(
        self, workspace_id: str, viewer_user_id: str, report_id: str
    ) -> InsightsSavedReport:
        uid = str(viewer_user_id)
        result = await self.db.execute(
            select(InsightsSavedReport).where(
                InsightsSavedReport.id == report_id,
                InsightsSavedReport.workspace_id == workspace_id,
                or_(
                    InsightsSavedReport.owner_user_id == uid,
                    InsightsSavedReport.visibility == VIS_WORKSPACE,
                ),
            )
        )
        row = result.scalar_one_or_none()
        if row is None:
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail="报表不存在",
            )
        return row

    def _ensure_can_share(self, actor_role: Optional[str], visibility: str) -> None:
        if visibility != VIS_WORKSPACE:
            return
        role = (actor_role or "").strip().lower()
        if role not in WRITER_ROLES:
            raise HTTPException(
                status_code=http_status.HTTP_403_FORBIDDEN,
                detail="仅 member/owner 可分享为工作区报表",
            )

    async def _ensure_cap(
        self,
        workspace_id: str,
        owner_user_id: str,
        visibility: str,
        *,
        exclude_report_id: Optional[str] = None,
    ) -> None:
        if visibility == VIS_WORKSPACE:
            q = (
                select(func.count())
                .select_from(InsightsSavedReport)
                .where(
                    InsightsSavedReport.workspace_id == workspace_id,
                    InsightsSavedReport.visibility == VIS_WORKSPACE,
                )
            )
            if exclude_report_id:
                q = q.where(InsightsSavedReport.id != exclude_report_id)
            count_q = await self.db.execute(q)
            if int(count_q.scalar_one() or 0) >= SHARED_REPORT_CAP:
                raise HTTPException(
                    status_code=http_status.HTTP_400_BAD_REQUEST,
                    detail=f"每工作区最多 {SHARED_REPORT_CAP} 份共享报表",
                )
            return
        q = (
            select(func.count())
            .select_from(InsightsSavedReport)
            .where(
                InsightsSavedReport.workspace_id == workspace_id,
                InsightsSavedReport.owner_user_id == str(owner_user_id),
                InsightsSavedReport.visibility == VIS_PERSONAL,
            )
        )
        if exclude_report_id:
            q = q.where(InsightsSavedReport.id != exclude_report_id)
        count_q = await self.db.execute(q)
        if int(count_q.scalar_one() or 0) >= REPORT_CAP:
            raise HTTPException(
                status_code=http_status.HTTP_400_BAD_REQUEST,
                detail=f"每用户每工作区最多 {REPORT_CAP} 份个人报表",
            )

    async def _clear_defaults(self, workspace_id: str, owner_user_id: str) -> None:
        await self.db.execute(
            update(InsightsSavedReport)
            .where(
                InsightsSavedReport.workspace_id == workspace_id,
                InsightsSavedReport.owner_user_id == str(owner_user_id),
                InsightsSavedReport.is_default.is_(True),
            )
            .values(is_default=False, updated_at=datetime.utcnow())
        )

    def _normalize_filters(self, filters: dict) -> dict[str, Any]:
        out: dict[str, Any] = {}
        if filters.get("projectId"):
            out["projectId"] = str(filters["projectId"])
        raw_ids = filters.get("labelIds")
        if raw_ids is not None:
            ids = normalize_label_ids(label_ids=list(raw_ids) if not isinstance(raw_ids, list) else raw_ids)
            if ids:
                out["labelIds"] = ids
        if filters.get("cycleId"):
            out["cycleId"] = str(filters["cycleId"])
        if filters.get("assigneeLimit") is not None:
            try:
                out["assigneeLimit"] = max(1, min(int(filters["assigneeLimit"]), 100))
            except (TypeError, ValueError):
                pass
        return out

    async def _ensure_filter_refs(self, workspace_id: str, filters: dict) -> None:
        if filters.get("projectId"):
            await self._ensure_project(workspace_id, filters["projectId"])
        if filters.get("labelIds"):
            await self._ensure_labels(workspace_id, filters["labelIds"])
        if filters.get("cycleId"):
            await self._resolve_cycle(workspace_id, filters["cycleId"])

    # ------------------------------------------------------------------ digest

    async def run_digest(
        self,
        *,
        workspace_id: str,
        actor_user_id: Optional[str] = None,
        today: Optional[date] = None,
    ) -> dict[str, Any]:
        """External tick: insights_digest Inbox (+ email via create). No cron."""
        from opentask.services.notification.service import NotificationService

        today = today or datetime.utcnow().date()
        notif = NotificationService(self.db)

        prefs_q = await self.db.execute(
            select(NotificationPreference).where(
                NotificationPreference.workspace_id == workspace_id,
                NotificationPreference.insights_digest.is_(True),
            )
        )
        pref_rows = list(prefs_q.scalars().all())

        created = 0
        skipped = 0
        errors: list[dict] = []

        for pref in pref_rows:
            user_id = str(pref.user_id)
            try:
                exists_q = await self.db.execute(
                    select(InsightsDigestDelivery.id).where(
                        InsightsDigestDelivery.workspace_id == workspace_id,
                        InsightsDigestDelivery.user_id == user_id,
                        InsightsDigestDelivery.bucket_date == today,
                    )
                )
                if exists_q.scalar_one_or_none() is not None:
                    skipped += 1
                    continue

                filters = await self._default_report_filters(workspace_id, user_id)
                summary = await self.summary(
                    workspace_id=workspace_id,
                    cycle_id=filters.get("cycleId"),
                    project_id=filters.get("projectId"),
                    label_ids=filters.get("labelIds"),
                    assignee_limit=filters.get("assigneeLimit") or DEFAULT_ASSIGNEE_LIMIT,
                )
                title, body = self._format_digest(summary)
                n = await notif.create(
                    workspace_id=workspace_id,
                    recipient_user_id=user_id,
                    actor_user_id=None,  # system tick
                    type="insights_digest",
                    resource_type="workspace",
                    resource_id=workspace_id,
                    title=title,
                    body=body,
                )
                if n is None:
                    skipped += 1
                    continue
                self.db.add(
                    InsightsDigestDelivery(
                        id=str(uuid.uuid4()),
                        workspace_id=workspace_id,
                        user_id=user_id,
                        bucket_date=today,
                        notification_id=getattr(n, "id", None),
                    )
                )
                await self.db.commit()
                created += 1
            except Exception as e:  # noqa: BLE001 — tick must continue
                errors.append({"userId": user_id, "message": str(e)[:500]})
                try:
                    await self.db.rollback()
                except Exception:
                    pass

        return {
            "created": created,
            "skipped": skipped,
            "errors": errors,
            "bucketDate": today.isoformat(),
            "eligible": len(pref_rows),
        }

    async def _default_report_filters(
        self, workspace_id: str, user_id: str
    ) -> dict[str, Any]:
        result = await self.db.execute(
            select(InsightsSavedReport).where(
                InsightsSavedReport.workspace_id == workspace_id,
                InsightsSavedReport.owner_user_id == str(user_id),
                InsightsSavedReport.is_default.is_(True),
            )
        )
        row = result.scalar_one_or_none()
        if row is None:
            return {}
        return dict(row.filters or {})

    def _format_digest(self, summary: dict[str, Any]) -> tuple[str, str]:
        status = summary.get("statusCounts") or {}
        top = sorted(status.items(), key=lambda kv: int(kv[1] or 0), reverse=True)[:5]
        top_s = ", ".join(f"{k}={v}" for k, v in top) or "(empty)"
        vel = summary.get("estimateVelocity") or {}
        pts = sum(float(b.get("completedPoints") or 0) for b in (vel.get("buckets") or []))
        trend = summary.get("createdVsCompleted") or []
        created = sum(int(d.get("created") or 0) for d in trend)
        completed = sum(int(d.get("completed") or 0) for d in trend)
        title = f"Insights digest · completedPts={pts:g}"
        body = (
            f"Status top: {top_s}\n"
            f"Last 14d created={created} completed={completed}\n"
            f"Velocity points={pts:g}"
        )
        return title[:255], body

    # ------------------------------------------------------------------ filters

    async def _ensure_filters(
        self,
        workspace_id: str,
        *,
        project_id: Optional[str],
        label_ids: Optional[list[int]],
    ) -> None:
        if project_id:
            await self._ensure_project(workspace_id, project_id)
        if label_ids:
            await self._ensure_labels(workspace_id, label_ids)

    async def _ensure_project(self, workspace_id: str, project_id: str) -> Project:
        result = await self.db.execute(
            select(Project).where(Project.id == project_id, Project.workspace_id == workspace_id)
        )
        project = result.scalar_one_or_none()
        if project is None:
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail="Project 不存在",
            )
        return project

    async def _ensure_label(self, workspace_id: str, label_id: int) -> Tag:
        result = await self.db.execute(
            select(Tag).where(Tag.id == label_id, Tag.workspace_id == workspace_id)
        )
        tag = result.scalar_one_or_none()
        if tag is None:
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail="Label 不存在",
            )
        return tag

    async def _ensure_labels(self, workspace_id: str, label_ids: list[int]) -> None:
        for lid in label_ids:
            await self._ensure_label(workspace_id, lid)

    def _base_issue_filter(
        self,
        workspace_id: str,
        *,
        project_id: Optional[str] = None,
        label_ids: Optional[list[int]] = None,
    ):
        clauses = [
            Issue.workspace_id == workspace_id,
            Issue.is_deleted.is_(False),
        ]
        if project_id:
            clauses.append(Issue.project_id == project_id)
        if label_ids:
            clauses.append(
                exists(
                    select(IssueTag.id).where(
                        IssueTag.issue_id == Issue.id,
                        IssueTag.tag_id.in_(list(label_ids)),
                    )
                )
            )
        return tuple(clauses)

    async def _status_counts(
        self,
        workspace_id: str,
        *,
        project_id: Optional[str] = None,
        label_ids: Optional[list[int]] = None,
    ) -> dict[str, int]:
        result = await self.db.execute(
            select(Issue.status, func.count())
            .where(
                *self._base_issue_filter(
                    workspace_id, project_id=project_id, label_ids=label_ids
                )
            )
            .group_by(Issue.status)
        )
        return {str(status): int(count) for status, count in result.all()}

    async def _priority_counts(
        self,
        workspace_id: str,
        *,
        project_id: Optional[str] = None,
        label_ids: Optional[list[int]] = None,
    ) -> dict[str, int]:
        result = await self.db.execute(
            select(Issue.priority, func.count())
            .where(
                *self._base_issue_filter(
                    workspace_id, project_id=project_id, label_ids=label_ids
                )
            )
            .group_by(Issue.priority)
        )
        return {str(priority): int(count) for priority, count in result.all()}

    async def _assignee_counts(
        self,
        workspace_id: str,
        *,
        limit: int,
        project_id: Optional[str] = None,
        label_ids: Optional[list[int]] = None,
    ) -> list[dict[str, Any]]:
        open_filter = (
            *self._base_issue_filter(
                workspace_id, project_id=project_id, label_ids=label_ids
            ),
            Issue.status.notin_(tuple(DONE_STATUSES)),
        )
        result = await self.db.execute(
            select(Issue.assignee_id, func.count().label("cnt"))
            .where(*open_filter)
            .group_by(Issue.assignee_id)
            .order_by(func.count().desc())
        )
        rows = list(result.all())
        unassigned_count = 0
        named: list[tuple[str, int]] = []
        for assignee_id, cnt in rows:
            if assignee_id is None:
                unassigned_count = int(cnt)
            else:
                named.append((str(assignee_id), int(cnt)))

        named = named[:limit]
        name_map: dict[str, str] = {}
        if named:
            ids = [aid for aid, _ in named]
            users = await self.db.execute(
                select(UserModel.id, UserModel.name, UserModel.username).where(
                    UserModel.id.in_(ids)
                )
            )
            for uid, name, username in users.all():
                name_map[str(uid)] = name or username or str(uid)

        out: list[dict[str, Any]] = []
        for aid, cnt in named:
            out.append(
                {
                    "assigneeId": aid,
                    "assigneeName": name_map.get(aid) or aid,
                    "count": cnt,
                }
            )
        out.append(
            {
                "assigneeId": None,
                "assigneeName": "Unassigned",
                "count": unassigned_count,
            }
        )
        return out

    async def _resolve_cycle(
        self, workspace_id: str, cycle_id: Optional[str]
    ) -> Optional[Cycle]:
        if cycle_id:
            result = await self.db.execute(
                select(Cycle).where(Cycle.id == cycle_id, Cycle.workspace_id == workspace_id)
            )
            cycle = result.scalar_one_or_none()
            if cycle is None:
                raise HTTPException(
                    status_code=http_status.HTTP_404_NOT_FOUND,
                    detail="Cycle 不存在",
                )
            return cycle
        result = await self.db.execute(
            select(Cycle)
            .where(Cycle.workspace_id == workspace_id, Cycle.status == "active")
            .order_by(Cycle.starts_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def _cycle_snapshot(
        self,
        workspace_id: str,
        *,
        cycle_id: Optional[str],
        project_id: Optional[str] = None,
        label_ids: Optional[list[int]] = None,
    ) -> Optional[dict[str, Any]]:
        cycle = await self._resolve_cycle(workspace_id, cycle_id)
        if cycle is None:
            return None
        extra = []
        if project_id:
            extra.append(Issue.project_id == project_id)
        if label_ids:
            extra.append(
                exists(
                    select(IssueTag.id).where(
                        IssueTag.issue_id == Issue.id,
                        IssueTag.tag_id.in_(list(label_ids)),
                    )
                )
            )
        result = await self.db.execute(
            select(
                func.count(),
                func.coalesce(
                    func.sum(
                        case(
                            (Issue.status.in_(tuple(DONE_STATUSES)), 1),
                            else_=0,
                        )
                    ),
                    0,
                ),
                func.coalesce(func.sum(Issue.estimate_points), 0),
            )
            .select_from(Issue)
            .where(
                Issue.cycle_id == cycle.id,
                Issue.workspace_id == workspace_id,
                Issue.is_deleted.is_(False),
                *extra,
            )
        )
        total, completed, points = result.one()
        return {
            "cycleId": cycle.id,
            "cycleName": cycle.name,
            "issueCount": int(total or 0),
            "completedCount": int(completed or 0),
            "estimatePointsSum": float(points or 0),
        }

    async def _created_vs_completed(
        self,
        workspace_id: str,
        *,
        days: int = TREND_DAYS,
        project_id: Optional[str] = None,
        label_ids: Optional[list[int]] = None,
    ) -> list[dict[str, Any]]:
        now = datetime.utcnow()
        start = (now - timedelta(days=days - 1)).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        base = self._base_issue_filter(
            workspace_id, project_id=project_id, label_ids=label_ids
        )

        created_q = await self.db.execute(
            select(func.date(Issue.created_at).label("d"), func.count().label("cnt"))
            .where(*base, Issue.created_at >= start)
            .group_by(func.date(Issue.created_at))
        )
        created_map = {str(d): int(c) for d, c in created_q.all()}

        completed_at = func.coalesce(Issue.closed_at, Issue.resolved_at)
        completed_q = await self.db.execute(
            select(func.date(completed_at).label("d"), func.count().label("cnt"))
            .where(
                *base,
                completed_at.is_not(None),
                completed_at >= start,
            )
            .group_by(func.date(completed_at))
        )
        completed_map = {str(d): int(c) for d, c in completed_q.all()}

        out: list[dict[str, Any]] = []
        for i in range(days):
            day = (start + timedelta(days=i)).strftime("%Y-%m-%d")
            out.append(
                {
                    "date": day,
                    "created": created_map.get(day, 0),
                    "completed": completed_map.get(day, 0),
                }
            )
        return out

    async def _estimate_velocity(
        self,
        workspace_id: str,
        *,
        days: int = VELOCITY_DAYS,
        project_id: Optional[str] = None,
        label_ids: Optional[list[int]] = None,
    ) -> dict[str, Any]:
        now = datetime.utcnow()
        start = (now - timedelta(days=days - 1)).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        base = self._base_issue_filter(
            workspace_id, project_id=project_id, label_ids=label_ids
        )
        completed_at = func.coalesce(Issue.closed_at, Issue.resolved_at)
        result = await self.db.execute(
            select(
                func.date(completed_at).label("d"),
                func.coalesce(func.sum(func.coalesce(Issue.estimate_points, 0)), 0),
            )
            .where(
                *base,
                completed_at.is_not(None),
                completed_at >= start,
            )
            .group_by(func.date(completed_at))
        )
        points_map = {str(d): float(pts or 0) for d, pts in result.all()}
        buckets: list[dict[str, Any]] = []
        for i in range(days):
            day = (start + timedelta(days=i)).strftime("%Y-%m-%d")
            buckets.append({"date": day, "completedPoints": points_map.get(day, 0.0)})
        return {"windowDays": days, "buckets": buckets}
