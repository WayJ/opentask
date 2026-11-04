"""Cycle 领域服务（E6-S1）"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from opentask.models.cycle.model import Cycle
from opentask.models.workspace.model import WorkspaceMember


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
        # allow naive ISO without tz
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
        await self.db.commit()
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
