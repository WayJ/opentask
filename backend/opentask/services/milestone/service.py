"""Milestone 领域服务（E8-S1 + E81 issue_count / status filter）"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from opentask.models.issue.model import Issue
from opentask.models.milestone.model import Milestone
from opentask.models.requirement.model import Project
from opentask.models.workspace.model import WorkspaceMember


def require_writer(member: WorkspaceMember) -> None:
    if member.role not in ("owner", "member"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="仅 member/owner 可写 Milestone",
        )


def serialize_milestone(m: Milestone, *, issue_count: int = 0) -> dict:
    """Q1a: always include issue_count (non-deleted issues same project+workspace)."""
    return {
        "id": m.id,
        "workspace_id": m.workspace_id,
        "project_id": m.project_id,
        "name": m.name,
        "description": m.description,
        "target_date": m.target_date,
        "status": m.status,
        "position": m.position,
        "created_at": m.created_at,
        "updated_at": m.updated_at,
        "issue_count": int(issue_count or 0),
    }


def _parse_dt(value) -> Optional[datetime]:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.replace(tzinfo=None) if value.tzinfo else value
    if not isinstance(value, str):
        raise HTTPException(status_code=400, detail="无效的日期时间")
    text = value.strip().replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(text)
        if dt.tzinfo is not None:
            return dt.replace(tzinfo=None)
        return dt
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="无效的日期时间") from exc


class MilestoneService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_project_in_workspace(
        self, *, project_id: str, workspace_id: str
    ) -> Project:
        result = await self.db.execute(
            select(Project).where(
                Project.id == project_id,
                Project.workspace_id == workspace_id,
            )
        )
        project = result.scalar_one_or_none()
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="项目不存在"
            )
        return project

    async def count_issues_by_milestone(
        self,
        *,
        project_id: str,
        workspace_id: str,
        milestone_ids: list[str],
    ) -> dict[str, int]:
        """Non-deleted issues in same project+workspace grouped by milestone_id."""
        if not milestone_ids:
            return {}
        q = (
            select(Issue.milestone_id, func.count())
            .where(
                Issue.workspace_id == workspace_id,
                Issue.project_id == project_id,
                Issue.milestone_id.in_(milestone_ids),
                Issue.is_deleted.is_(False),
            )
            .group_by(Issue.milestone_id)
        )
        rows = (await self.db.execute(q)).all()
        counts = {mid: 0 for mid in milestone_ids}
        for mid, cnt in rows:
            if mid is not None:
                counts[mid] = int(cnt)
        return counts

    async def list(
        self,
        *,
        project_id: str,
        workspace_id: str,
        status: Optional[str] = None,
    ) -> list[Milestone]:
        await self.get_project_in_workspace(
            project_id=project_id, workspace_id=workspace_id
        )
        if status is not None:
            if status not in ("planned", "done"):
                raise HTTPException(status_code=400, detail="无效的 status")
        q = (
            select(Milestone)
            .where(
                Milestone.project_id == project_id,
                Milestone.workspace_id == workspace_id,
            )
            .order_by(Milestone.position.asc(), Milestone.created_at.asc())
        )
        if status is not None:
            q = q.where(Milestone.status == status)
        return list((await self.db.execute(q)).scalars().all())

    async def get(
        self, milestone_id: str, *, project_id: str, workspace_id: str
    ) -> Optional[Milestone]:
        result = await self.db.execute(
            select(Milestone).where(
                Milestone.id == milestone_id,
                Milestone.project_id == project_id,
                Milestone.workspace_id == workspace_id,
            )
        )
        return result.scalar_one_or_none()

    async def create(
        self,
        *,
        project_id: str,
        workspace_id: str,
        name: str,
        description: Optional[str] = None,
        target_date=None,
        status: str = "planned",
        position: int = 0,
    ) -> Milestone:
        await self.get_project_in_workspace(
            project_id=project_id, workspace_id=workspace_id
        )
        name = (name or "").strip()
        if not name:
            raise HTTPException(status_code=400, detail="名称不能为空")
        if status not in ("planned", "done"):
            raise HTTPException(status_code=400, detail="无效的 status")
        now = datetime.utcnow()
        row = Milestone(
            workspace_id=workspace_id,
            project_id=project_id,
            name=name[:255],
            description=description,
            target_date=_parse_dt(target_date),
            status=status,
            position=int(position or 0),
            created_at=now,
            updated_at=now,
        )
        self.db.add(row)
        await self.db.commit()
        await self.db.refresh(row)
        return row

    async def update(
        self,
        row: Milestone,
        *,
        name: Optional[str] = None,
        description: Optional[str] = None,
        target_date=...,
        status: Optional[str] = None,
        position: Optional[int] = None,
    ) -> Milestone:
        if name is not None:
            name = name.strip()
            if not name:
                raise HTTPException(status_code=400, detail="名称不能为空")
            row.name = name[:255]
        if description is not None:
            row.description = description
        if target_date is not ...:
            row.target_date = _parse_dt(target_date)
        if status is not None:
            if status not in ("planned", "done"):
                raise HTTPException(status_code=400, detail="无效的 status")
            row.status = status
        if position is not None:
            row.position = int(position)
        row.updated_at = datetime.utcnow()
        await self.db.commit()
        await self.db.refresh(row)
        return row

    async def delete(self, row: Milestone) -> None:
        await self.db.delete(row)
        await self.db.commit()
