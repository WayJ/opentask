"""Initiative service (E10-S1)"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from fastapi import HTTPException, status as http_status
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from opentask.models.initiative.model import INITIATIVE_STATUSES, Initiative, InitiativeProject
from opentask.models.requirement.model import Project
from opentask.models.workspace.model import WorkspaceMember


def require_writer(member: WorkspaceMember) -> None:
    if member.role not in ("owner", "member"):
        raise HTTPException(
            status_code=http_status.HTTP_403_FORBIDDEN,
            detail="仅 member/owner 可写",
        )


_HEALTH_RANK = {"off_track": 3, "at_risk": 2, "on_track": 1}


def compute_health_summary(statuses: list[str | None]) -> dict:
    """Worst-of rollup over Project.health_status values (E10-S2)."""
    counts = {"onTrack": 0, "atRisk": 0, "offTrack": 0, "unknown": 0}
    best_rank = 0
    overall: str | None = None
    for raw in statuses:
        if raw == "on_track":
            counts["onTrack"] += 1
            rank = _HEALTH_RANK["on_track"]
        elif raw == "at_risk":
            counts["atRisk"] += 1
            rank = _HEALTH_RANK["at_risk"]
        elif raw == "off_track":
            counts["offTrack"] += 1
            rank = _HEALTH_RANK["off_track"]
        else:
            counts["unknown"] += 1
            rank = 0
        if rank > best_rank:
            best_rank = rank
            overall = raw
    if not statuses:
        overall = None
    elif best_rank == 0:
        overall = None
    return {
        "overall": overall,
        "counts": counts,
        "projectCount": len(statuses),
    }


def empty_health_summary() -> dict:
    return compute_health_summary([])


def serialize_initiative(
    row: Initiative,
    project_ids: list[str] | None = None,
    *,
    health_summary: dict | None = None,
    projects: list[dict] | None = None,
) -> dict:
    data = {
        "id": row.id,
        "workspaceId": row.workspace_id,
        "name": row.name,
        "description": row.description,
        "status": row.status,
        "targetDate": row.target_date.isoformat() if row.target_date else None,
        "ownerUserId": row.owner_user_id,
        "sortOrder": row.sort_order,
        "projectIds": list(project_ids or []),
        "healthSummary": health_summary if health_summary is not None else empty_health_summary(),
        "createdBy": row.created_by,
        "createdAt": row.created_at.isoformat() if row.created_at else None,
        "updatedAt": row.updated_at.isoformat() if row.updated_at else None,
    }
    if projects is not None:
        data["projects"] = projects
    return data


class InitiativeService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def _project_ids_for(self, initiative_id: str) -> list[str]:
        result = await self.db.execute(
            select(InitiativeProject.project_id).where(
                InitiativeProject.initiative_id == initiative_id
            )
        )
        return [r[0] for r in result.all()]

    async def _project_ids_map(self, initiative_ids: list[str]) -> dict[str, list[str]]:
        if not initiative_ids:
            return {}
        result = await self.db.execute(
            select(InitiativeProject.initiative_id, InitiativeProject.project_id).where(
                InitiativeProject.initiative_id.in_(initiative_ids)
            )
        )
        out: dict[str, list[str]] = {i: [] for i in initiative_ids}
        for iid, pid in result.all():
            out.setdefault(iid, []).append(pid)
        return out

    async def get(self, *, workspace_id: str, initiative_id: str) -> Initiative:
        result = await self.db.execute(
            select(Initiative).where(
                Initiative.id == initiative_id,
                Initiative.workspace_id == workspace_id,
            )
        )
        row = result.scalar_one_or_none()
        if not row:
            raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail="Initiative 不存在")
        return row

    async def list(self, *, workspace_id: str) -> list[tuple[Initiative, list[str]]]:
        result = await self.db.execute(
            select(Initiative)
            .where(Initiative.workspace_id == workspace_id)
            .order_by(Initiative.sort_order.asc(), Initiative.created_at.desc())
        )
        rows = list(result.scalars().all())
        pmap = await self._project_ids_map([r.id for r in rows])
        return [(r, pmap.get(r.id, [])) for r in rows]

    async def _validate_projects(self, *, workspace_id: str, project_ids: list[str]) -> None:
        if not project_ids:
            return
        unique = list(dict.fromkeys(project_ids))
        result = await self.db.execute(
            select(Project.id).where(
                Project.id.in_(unique),
                Project.workspace_id == workspace_id,
            )
        )
        found = {r[0] for r in result.all()}
        missing = [pid for pid in unique if pid not in found]
        if missing:
            raise HTTPException(
                status_code=http_status.HTTP_400_BAD_REQUEST,
                detail=f"项目不存在或不属于当前工作区: {', '.join(missing)}",
            )

    async def _replace_projects(self, *, initiative_id: str, project_ids: list[str]) -> None:
        await self.db.execute(
            delete(InitiativeProject).where(InitiativeProject.initiative_id == initiative_id)
        )
        now = datetime.utcnow()
        for pid in dict.fromkeys(project_ids):
            self.db.add(
                InitiativeProject(
                    initiative_id=initiative_id,
                    project_id=pid,
                    created_at=now,
                )
            )

    async def create(
        self,
        *,
        workspace_id: str,
        user_id: str,
        name: str,
        description: Optional[str] = None,
        status: str = "active",
        target_date: Optional[datetime] = None,
        owner_user_id: Optional[str] = None,
        sort_order: int = 0,
        project_ids: Optional[list[str]] = None,
    ) -> tuple[Initiative, list[str]]:
        if status not in INITIATIVE_STATUSES:
            raise HTTPException(
                status_code=http_status.HTTP_400_BAD_REQUEST,
                detail=f"非法 status，允许: {', '.join(INITIATIVE_STATUSES)}",
            )
        project_ids = project_ids or []
        await self._validate_projects(workspace_id=workspace_id, project_ids=project_ids)
        now = datetime.utcnow()
        row = Initiative(
            workspace_id=workspace_id,
            name=name.strip(),
            description=description,
            status=status,
            target_date=target_date,
            owner_user_id=owner_user_id,
            sort_order=sort_order,
            created_by=user_id,
            created_at=now,
            updated_at=now,
        )
        self.db.add(row)
        try:
            await self.db.flush()
        except IntegrityError:
            await self.db.rollback()
            raise HTTPException(
                status_code=http_status.HTTP_409_CONFLICT,
                detail="同名 Initiative 已存在",
            )
        await self._replace_projects(initiative_id=row.id, project_ids=project_ids)
        await self.db.commit()
        await self.db.refresh(row)
        return row, list(dict.fromkeys(project_ids))

    async def update(
        self,
        *,
        workspace_id: str,
        initiative_id: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        status: Optional[str] = None,
        target_date: Optional[datetime] = None,
        clear_target_date: bool = False,
        owner_user_id: Optional[str] = None,
        clear_owner: bool = False,
        sort_order: Optional[int] = None,
        project_ids: Optional[list[str]] = None,
    ) -> tuple[Initiative, list[str]]:
        row = await self.get(workspace_id=workspace_id, initiative_id=initiative_id)
        if name is not None:
            row.name = name.strip()
        if description is not None:
            row.description = description
        if status is not None:
            if status not in INITIATIVE_STATUSES:
                raise HTTPException(
                    status_code=http_status.HTTP_400_BAD_REQUEST,
                    detail=f"非法 status，允许: {', '.join(INITIATIVE_STATUSES)}",
                )
            row.status = status
        if clear_target_date:
            row.target_date = None
        elif target_date is not None:
            row.target_date = target_date
        if clear_owner:
            row.owner_user_id = None
        elif owner_user_id is not None:
            row.owner_user_id = owner_user_id
        if sort_order is not None:
            row.sort_order = sort_order
        if project_ids is not None:
            await self._validate_projects(workspace_id=workspace_id, project_ids=project_ids)
            await self._replace_projects(initiative_id=row.id, project_ids=project_ids)
        row.updated_at = datetime.utcnow()
        try:
            await self.db.commit()
        except IntegrityError:
            await self.db.rollback()
            raise HTTPException(
                status_code=http_status.HTTP_409_CONFLICT,
                detail="同名 Initiative 已存在",
            )
        await self.db.refresh(row)
        pids = await self._project_ids_for(row.id)
        return row, pids

    async def delete(self, *, workspace_id: str, initiative_id: str) -> None:
        row = await self.get(workspace_id=workspace_id, initiative_id=initiative_id)
        await self.db.delete(row)
        await self.db.commit()

    async def set_projects(
        self, *, workspace_id: str, initiative_id: str, project_ids: list[str]
    ) -> tuple[Initiative, list[str]]:
        row = await self.get(workspace_id=workspace_id, initiative_id=initiative_id)
        await self._validate_projects(workspace_id=workspace_id, project_ids=project_ids)
        await self._replace_projects(initiative_id=row.id, project_ids=project_ids)
        row.updated_at = datetime.utcnow()
        await self.db.commit()
        await self.db.refresh(row)
        return row, list(dict.fromkeys(project_ids))

    async def attach_project(
        self, *, workspace_id: str, initiative_id: str, project_id: str
    ) -> tuple[Initiative, list[str]]:
        row = await self.get(workspace_id=workspace_id, initiative_id=initiative_id)
        await self._validate_projects(workspace_id=workspace_id, project_ids=[project_id])
        existing = await self._project_ids_for(row.id)
        if project_id not in existing:
            self.db.add(
                InitiativeProject(
                    initiative_id=row.id,
                    project_id=project_id,
                    created_at=datetime.utcnow(),
                )
            )
            row.updated_at = datetime.utcnow()
            await self.db.commit()
            await self.db.refresh(row)
            existing = existing + [project_id]
        return row, existing

    async def detach_project(
        self, *, workspace_id: str, initiative_id: str, project_id: str
    ) -> tuple[Initiative, list[str]]:
        row = await self.get(workspace_id=workspace_id, initiative_id=initiative_id)
        await self.db.execute(
            delete(InitiativeProject).where(
                InitiativeProject.initiative_id == row.id,
                InitiativeProject.project_id == project_id,
            )
        )
        row.updated_at = datetime.utcnow()
        await self.db.commit()
        await self.db.refresh(row)
        pids = await self._project_ids_for(row.id)
        return row, pids

    async def _projects_health(
        self, project_ids: list[str]
    ) -> tuple[dict, list[dict]]:
        if not project_ids:
            return empty_health_summary(), []
        result = await self.db.execute(
            select(Project.id, Project.name, Project.health_status).where(
                Project.id.in_(project_ids)
            )
        )
        by_id = {r[0]: (r[1], r[2]) for r in result.all()}
        statuses: list[str | None] = []
        projects: list[dict] = []
        for pid in project_ids:
            name, hs = by_id.get(pid, (None, None))
            statuses.append(hs)
            projects.append(
                {
                    "id": pid,
                    "name": name,
                    "healthStatus": hs,
                }
            )
        return compute_health_summary(statuses), projects

    async def to_response(
        self,
        row: Initiative,
        project_ids: list[str] | None = None,
        *,
        include_projects: bool = False,
    ) -> dict:
        pids = list(project_ids if project_ids is not None else await self._project_ids_for(row.id))
        summary, projects = await self._projects_health(pids)
        return serialize_initiative(
            row,
            pids,
            health_summary=summary,
            projects=projects if include_projects else None,
        )
