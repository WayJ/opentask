"""Workspace Insights 只读聚合（E24）。"""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Optional

from fastapi import HTTPException, status as http_status
from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from opentask.models.cycle.model import Cycle
from opentask.models.issue.model import Issue
from opentask.models.user.model import UserModel

DONE_STATUSES = frozenset({"resolved", "closed"})
DEFAULT_ASSIGNEE_LIMIT = 10
TREND_DAYS = 14


class InsightsService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def summary(
        self,
        *,
        workspace_id: str,
        cycle_id: Optional[str] = None,
        assignee_limit: int = DEFAULT_ASSIGNEE_LIMIT,
    ) -> dict[str, Any]:
        limit = max(1, min(int(assignee_limit or DEFAULT_ASSIGNEE_LIMIT), 100))
        status_counts = await self._status_counts(workspace_id)
        priority_counts = await self._priority_counts(workspace_id)
        assignee_counts = await self._assignee_counts(workspace_id, limit=limit)
        cycle_snapshot = await self._cycle_snapshot(workspace_id, cycle_id=cycle_id)
        created_vs_completed = await self._created_vs_completed(workspace_id, days=TREND_DAYS)
        return {
            "statusCounts": status_counts,
            "priorityCounts": priority_counts,
            "assigneeCounts": assignee_counts,
            "cycleSnapshot": cycle_snapshot,
            "createdVsCompleted": created_vs_completed,
        }

    def _base_issue_filter(self, workspace_id: str):
        return (
            Issue.workspace_id == workspace_id,
            Issue.is_deleted.is_(False),
        )

    async def _status_counts(self, workspace_id: str) -> dict[str, int]:
        result = await self.db.execute(
            select(Issue.status, func.count())
            .where(*self._base_issue_filter(workspace_id))
            .group_by(Issue.status)
        )
        return {str(status): int(count) for status, count in result.all()}

    async def _priority_counts(self, workspace_id: str) -> dict[str, int]:
        result = await self.db.execute(
            select(Issue.priority, func.count())
            .where(*self._base_issue_filter(workspace_id))
            .group_by(Issue.priority)
        )
        return {str(priority): int(count) for priority, count in result.all()}

    async def _assignee_counts(self, workspace_id: str, *, limit: int) -> list[dict[str, Any]]:
        """开放 Issue（非 DONE）按 assignee；unassigned 始终保留；具名 top N。"""
        open_filter = (
            *self._base_issue_filter(workspace_id),
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
                select(UserModel.id, UserModel.name, UserModel.username).where(UserModel.id.in_(ids))
            )
            for uid, name, username in users.all():
                name_map[str(uid)] = (name or username or str(uid))

        out: list[dict[str, Any]] = []
        for aid, cnt in named:
            out.append(
                {
                    "assigneeId": aid,
                    "assigneeName": name_map.get(aid) or aid,
                    "count": cnt,
                }
            )
        # 始终附带 unassigned，便于 FE 展示空负荷
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
        self, workspace_id: str, *, cycle_id: Optional[str]
    ) -> Optional[dict[str, Any]]:
        cycle = await self._resolve_cycle(workspace_id, cycle_id)
        if cycle is None:
            return None
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
        self, workspace_id: str, *, days: int = TREND_DAYS
    ) -> list[dict[str, Any]]:
        now = datetime.utcnow()
        start = (now - timedelta(days=days - 1)).replace(hour=0, minute=0, second=0, microsecond=0)

        created_q = await self.db.execute(
            select(func.date(Issue.created_at).label("d"), func.count().label("cnt"))
            .where(
                *self._base_issue_filter(workspace_id),
                Issue.created_at >= start,
            )
            .group_by(func.date(Issue.created_at))
        )
        created_map = {str(d): int(c) for d, c in created_q.all()}

        completed_at = func.coalesce(Issue.closed_at, Issue.resolved_at)
        completed_q = await self.db.execute(
            select(func.date(completed_at).label("d"), func.count().label("cnt"))
            .where(
                *self._base_issue_filter(workspace_id),
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
