"""Workspace Insights 只读聚合（E24 + E55 thicken）。"""
from __future__ import annotations

import csv
import io
from datetime import datetime, timedelta
from typing import Any, Optional

from fastapi import HTTPException, status as http_status
from sqlalchemy import case, exists, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from opentask.models.cycle.model import Cycle
from opentask.models.issue.model import Issue, IssueTag
from opentask.models.requirement.model import Project
from opentask.models.tag.model import Tag
from opentask.models.user.model import UserModel

DONE_STATUSES = frozenset({"resolved", "closed"})
DEFAULT_ASSIGNEE_LIMIT = 10
TREND_DAYS = 14
VELOCITY_DAYS = 14


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
    ) -> dict[str, Any]:
        await self._ensure_filters(workspace_id, project_id=project_id, label_id=label_id)
        limit = max(1, min(int(assignee_limit or DEFAULT_ASSIGNEE_LIMIT), 100))
        status_counts = await self._status_counts(
            workspace_id, project_id=project_id, label_id=label_id
        )
        priority_counts = await self._priority_counts(
            workspace_id, project_id=project_id, label_id=label_id
        )
        assignee_counts = await self._assignee_counts(
            workspace_id, limit=limit, project_id=project_id, label_id=label_id
        )
        cycle_snapshot = await self._cycle_snapshot(
            workspace_id, cycle_id=cycle_id, project_id=project_id, label_id=label_id
        )
        created_vs_completed = await self._created_vs_completed(
            workspace_id, days=TREND_DAYS, project_id=project_id, label_id=label_id
        )
        estimate_velocity = await self._estimate_velocity(
            workspace_id, days=VELOCITY_DAYS, project_id=project_id, label_id=label_id
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
    ) -> str:
        data = await self.summary(
            workspace_id=workspace_id,
            cycle_id=cycle_id,
            assignee_limit=assignee_limit,
            project_id=project_id,
            label_id=label_id,
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

    async def _ensure_filters(
        self,
        workspace_id: str,
        *,
        project_id: Optional[str],
        label_id: Optional[int],
    ) -> None:
        if project_id:
            await self._ensure_project(workspace_id, project_id)
        if label_id is not None:
            await self._ensure_label(workspace_id, label_id)

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

    def _base_issue_filter(
        self,
        workspace_id: str,
        *,
        project_id: Optional[str] = None,
        label_id: Optional[int] = None,
    ):
        clauses = [
            Issue.workspace_id == workspace_id,
            Issue.is_deleted.is_(False),
        ]
        if project_id:
            clauses.append(Issue.project_id == project_id)
        if label_id is not None:
            clauses.append(
                exists(
                    select(IssueTag.id).where(
                        IssueTag.issue_id == Issue.id,
                        IssueTag.tag_id == label_id,
                    )
                )
            )
        return tuple(clauses)

    async def _status_counts(
        self,
        workspace_id: str,
        *,
        project_id: Optional[str] = None,
        label_id: Optional[int] = None,
    ) -> dict[str, int]:
        result = await self.db.execute(
            select(Issue.status, func.count())
            .where(
                *self._base_issue_filter(
                    workspace_id, project_id=project_id, label_id=label_id
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
        label_id: Optional[int] = None,
    ) -> dict[str, int]:
        result = await self.db.execute(
            select(Issue.priority, func.count())
            .where(
                *self._base_issue_filter(
                    workspace_id, project_id=project_id, label_id=label_id
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
        label_id: Optional[int] = None,
    ) -> list[dict[str, Any]]:
        """开放 Issue（非 DONE）按 assignee；unassigned 始终保留；具名 top N。"""
        open_filter = (
            *self._base_issue_filter(
                workspace_id, project_id=project_id, label_id=label_id
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
        label_id: Optional[int] = None,
    ) -> Optional[dict[str, Any]]:
        cycle = await self._resolve_cycle(workspace_id, cycle_id)
        if cycle is None:
            return None
        # Q2a: project/label also narrow cycleSnapshot
        extra = []
        if project_id:
            extra.append(Issue.project_id == project_id)
        if label_id is not None:
            extra.append(
                exists(
                    select(IssueTag.id).where(
                        IssueTag.issue_id == Issue.id,
                        IssueTag.tag_id == label_id,
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
        label_id: Optional[int] = None,
    ) -> list[dict[str, Any]]:
        now = datetime.utcnow()
        start = (now - timedelta(days=days - 1)).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        base = self._base_issue_filter(
            workspace_id, project_id=project_id, label_id=label_id
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
        label_id: Optional[int] = None,
    ) -> dict[str, Any]:
        now = datetime.utcnow()
        start = (now - timedelta(days=days - 1)).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        base = self._base_issue_filter(
            workspace_id, project_id=project_id, label_id=label_id
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
