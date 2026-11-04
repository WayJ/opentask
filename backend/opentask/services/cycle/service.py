"""Cycle 领域服务（E6-S1/S3）"""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from opentask.models.cycle.model import Cycle
from opentask.models.issue.model import Issue
from opentask.models.workspace.model import Workspace, WorkspaceMember

DONE_STATUSES = frozenset({"resolved", "closed"})


def require_writer(member: WorkspaceMember) -> None:
    if member.role not in ("owner", "member"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="仅 member/owner 可写 Cycle",
        )


def serialize_cycle(c: Cycle) -> dict:
    return {
        "id": c.id,
        "workspaceId": c.workspace_id,
        "name": c.name,
        "number": c.number,
        "status": c.status,
        "startsAt": c.starts_at,
        "endsAt": c.ends_at,
        "completedAt": c.completed_at,
        "createdAt": c.created_at,
        "updatedAt": c.updated_at,
    }


def _parse_dt(value) -> datetime:
    if isinstance(value, datetime):
        return value
    if not isinstance(value, str):
        raise HTTPException(status_code=400, detail="无效的日期时间")
    text = value.strip().replace("Z", "+00:00")
    try:
        if "+" in text[10:] or text.endswith("Z"):
            return datetime.fromisoformat(text).replace(tzinfo=None)
        return datetime.fromisoformat(text)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="无效的日期时间") from exc


class CycleService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list(
        self, *, workspace_id: str, status_filter: Optional[str] = None
    ) -> list[Cycle]:
        q = select(Cycle).where(Cycle.workspace_id == workspace_id)
        if status_filter:
            q = q.where(Cycle.status == status_filter)
        q = q.order_by(Cycle.starts_at.asc(), Cycle.created_at.asc())
        return list((await self.db.execute(q)).scalars().all())

    async def get(self, cycle_id: str, *, workspace_id: str) -> Optional[Cycle]:
        result = await self.db.execute(
            select(Cycle).where(Cycle.id == cycle_id, Cycle.workspace_id == workspace_id)
        )
        return result.scalar_one_or_none()

    async def _next_number(self, workspace_id: str) -> int:
        result = await self.db.execute(
            select(func.max(Cycle.number)).where(Cycle.workspace_id == workspace_id)
        )
        current = result.scalar_one_or_none()
        return int(current or 0) + 1

    async def create(
        self,
        *,
        workspace_id: str,
        starts_at,
        ends_at,
        name: Optional[str] = None,
        status: str = "upcoming",
        commit: bool = True,
    ) -> Cycle:
        starts = _parse_dt(starts_at)
        ends = _parse_dt(ends_at)
        if ends <= starts:
            raise HTTPException(status_code=400, detail="ends_at 必须晚于 starts_at")
        if status not in ("upcoming", "active", "completed"):
            raise HTTPException(status_code=400, detail="无效的 status")
        if status == "active":
            await self._ensure_no_active(workspace_id)
        number = await self._next_number(workspace_id)
        final_name = (name or "").strip()[:128] or f"Cycle {number}"
        now = datetime.utcnow()
        row = Cycle(
            workspace_id=workspace_id,
            name=final_name,
            number=number,
            status=status,
            starts_at=starts,
            ends_at=ends,
            completed_at=now if status == "completed" else None,
            created_at=now,
            updated_at=now,
        )
        self.db.add(row)
        if commit:
            await self.db.commit()
            await self.db.refresh(row)
        else:
            await self.db.flush()
            await self.db.refresh(row)
        return row

    async def update(
        self,
        cycle: Cycle,
        *,
        name: Optional[str] = None,
        starts_at=None,
        ends_at=None,
    ) -> Cycle:
        if cycle.status == "completed" and (starts_at is not None or ends_at is not None):
            raise HTTPException(status_code=400, detail="已完成 Cycle 不可改日期")
        if name is not None:
            cycle.name = name.strip()[:128] or cycle.name
        new_starts = _parse_dt(starts_at) if starts_at is not None else cycle.starts_at
        new_ends = _parse_dt(ends_at) if ends_at is not None else cycle.ends_at
        if new_ends <= new_starts:
            raise HTTPException(status_code=400, detail="ends_at 必须晚于 starts_at")
        cycle.starts_at = new_starts
        cycle.ends_at = new_ends
        cycle.updated_at = datetime.utcnow()
        await self.db.commit()
        await self.db.refresh(cycle)
        return cycle

    async def delete(self, cycle: Cycle) -> None:
        if cycle.status != "upcoming":
            raise HTTPException(status_code=400, detail="仅可删除 upcoming Cycle")
        await self.db.delete(cycle)
        await self.db.commit()

    async def _ensure_no_active(self, workspace_id: str, *, exclude_id: str | None = None) -> None:
        q = select(Cycle.id).where(
            Cycle.workspace_id == workspace_id, Cycle.status == "active"
        )
        if exclude_id:
            q = q.where(Cycle.id != exclude_id)
        existing = (await self.db.execute(q.limit(1))).scalar_one_or_none()
        if existing:
            raise HTTPException(status_code=400, detail="工作区已有 active Cycle，请先结束当前冲刺")

    async def activate(self, cycle: Cycle) -> Cycle:
        if cycle.status != "upcoming":
            raise HTTPException(status_code=400, detail="仅 upcoming 可激活")
        await self._ensure_no_active(cycle.workspace_id, exclude_id=cycle.id)
        cycle.status = "active"
        cycle.updated_at = datetime.utcnow()
        await self.db.commit()
        await self.db.refresh(cycle)
        return cycle

    async def _load_workspace(self, workspace_id: str) -> Workspace:
        result = await self.db.execute(select(Workspace).where(Workspace.id == workspace_id))
        ws = result.scalar_one_or_none()
        if not ws:
            raise HTTPException(status_code=404, detail="工作区不存在")
        return ws

    async def _latest_ends_at(self, workspace_id: str) -> Optional[datetime]:
        result = await self.db.execute(
            select(func.max(Cycle.ends_at)).where(Cycle.workspace_id == workspace_id)
        )
        return result.scalar_one_or_none()

    async def generate_upcoming(
        self, *, workspace: Workspace, commit: bool = True
    ) -> Cycle:
        duration = int(workspace.cycle_duration_days or 14)
        if duration < 1:
            duration = 14
        now = datetime.utcnow()
        latest_end = await self._latest_ends_at(workspace.id)
        starts = latest_end if latest_end and latest_end > now else now
        # normalize naive
        if getattr(starts, "tzinfo", None) is not None:
            starts = starts.replace(tzinfo=None)
        ends = starts + timedelta(days=duration)
        return await self.create(
            workspace_id=workspace.id,
            starts_at=starts,
            ends_at=ends,
            status="upcoming",
            commit=commit,
        )

    async def _find_next_upcoming(self, cycle: Cycle) -> Optional[Cycle]:
        preferred = await self.db.execute(
            select(Cycle)
            .where(
                Cycle.workspace_id == cycle.workspace_id,
                Cycle.status == "upcoming",
                Cycle.starts_at >= cycle.ends_at,
            )
            .order_by(Cycle.starts_at.asc(), Cycle.created_at.asc())
            .limit(1)
        )
        row = preferred.scalar_one_or_none()
        if row:
            return row
        fallback = await self.db.execute(
            select(Cycle)
            .where(
                Cycle.workspace_id == cycle.workspace_id,
                Cycle.status == "upcoming",
            )
            .order_by(Cycle.starts_at.asc(), Cycle.created_at.asc())
            .limit(1)
        )
        return fallback.scalar_one_or_none()

    async def _incomplete_issue_ids(self, cycle_id: str) -> list[str]:
        result = await self.db.execute(
            select(Issue.id).where(
                Issue.cycle_id == cycle_id,
                Issue.status.notin_(tuple(DONE_STATUSES)),
            )
        )
        return [row[0] for row in result.all()]

    async def complete(self, cycle: Cycle, *, workspace: Workspace) -> dict:
        if cycle.status != "active":
            raise HTTPException(status_code=400, detail="仅 active Cycle 可结束")
        if cycle.workspace_id != workspace.id:
            raise HTTPException(status_code=404, detail="Cycle 不存在")

        policy = (workspace.cycle_rollover_policy or "into_next").strip()
        if policy not in ("into_next", "leave_unassigned"):
            policy = "into_next"

        incomplete_ids = await self._incomplete_issue_ids(cycle.id)
        next_cycle: Optional[Cycle] = None
        rolled_count = 0

        if incomplete_ids:
            if policy == "into_next":
                next_cycle = await self._find_next_upcoming(cycle)
                if not next_cycle:
                    next_cycle = await self.generate_upcoming(workspace=workspace, commit=False)
                await self.db.execute(
                    update(Issue)
                    .where(Issue.id.in_(incomplete_ids))
                    .values(cycle_id=next_cycle.id)
                )
                rolled_count = len(incomplete_ids)
            else:
                await self.db.execute(
                    update(Issue)
                    .where(Issue.id.in_(incomplete_ids))
                    .values(cycle_id=None)
                )
                rolled_count = len(incomplete_ids)

        now = datetime.utcnow()
        cycle.status = "completed"
        cycle.completed_at = now
        cycle.updated_at = now
        await self.db.commit()
        await self.db.refresh(cycle)
        if next_cycle is not None:
            await self.db.refresh(next_cycle)

        return {
            "cycle": cycle,
            "rolledCount": rolled_count,
            "nextCycleId": next_cycle.id if next_cycle else None,
            "policy": policy,
        }

    async def _member_count(self, workspace_id: str) -> int:
        result = await self.db.execute(
            select(func.count())
            .select_from(WorkspaceMember)
            .where(WorkspaceMember.workspace_id == workspace_id)
        )
        return int(result.scalar_one() or 0)

    async def _completed_issue_count(self, cycle_id: str) -> int:
        result = await self.db.execute(
            select(func.count())
            .select_from(Issue)
            .where(
                Issue.cycle_id == cycle_id,
                Issue.status.in_(tuple(DONE_STATUSES)),
            )
        )
        return int(result.scalar_one() or 0)

    async def capacity_hint(
        self, *, workspace: Workspace, cycle_id: Optional[str] = None
    ) -> dict:
        lookback = int(workspace.cycle_capacity_lookback or 3)
        if lookback < 1:
            lookback = 3

        completed = await self.db.execute(
            select(Cycle)
            .where(
                Cycle.workspace_id == workspace.id,
                Cycle.status == "completed",
            )
            .order_by(Cycle.completed_at.desc().nullslast(), Cycle.ends_at.desc())
            .limit(lookback)
        )
        cycles = list(completed.scalars().all())
        samples: list[dict] = []
        for c in cycles:
            count = await self._completed_issue_count(c.id)
            samples.append(
                {
                    "cycleId": c.id,
                    "name": c.name,
                    "completedIssueCount": count,
                }
            )

        if samples:
            mean = sum(s["completedIssueCount"] for s in samples) / len(samples)
            # integer-friendly if whole number
            suggested = int(mean) if float(mean).is_integer() else round(mean, 2)
            return {
                "basis": "history",
                "suggestedCapacity": suggested,
                "lookbackN": lookback,
                "samples": samples,
                "cycleId": cycle_id,
            }

        members = await self._member_count(workspace.id)
        return {
            "basis": "members",
            "suggestedCapacity": members,
            "lookbackN": lookback,
            "samples": [],
            "cycleId": cycle_id,
        }
