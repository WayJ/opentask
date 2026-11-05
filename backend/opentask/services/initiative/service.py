"""Initiative service (E10-S1)"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from fastapi import HTTPException, status as http_status
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from opentask.models.initiative.model import (
    INITIATIVE_RELATION_TYPES,
    INITIATIVE_STATUSES,
    Initiative,
    InitiativeProject,
    InitiativeRelation,
)
from opentask.models.requirement.model import Project
from opentask.models.workspace.model import WorkspaceMember

_BLOCKS_CYCLE_DEPTH_CAP = 32


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
    relation_counts: dict | None = None,
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
    if relation_counts is not None:
        data["blocksCount"] = int(relation_counts.get("blocksCount", 0))
        data["blockedByCount"] = int(relation_counts.get("blockedByCount", 0))
        data["relatesToCount"] = int(relation_counts.get("relatesToCount", 0))
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
        include_relation_counts: bool = False,
    ) -> dict:
        pids = list(project_ids if project_ids is not None else await self._project_ids_for(row.id))
        summary, projects = await self._projects_health(pids)
        counts = None
        if include_relation_counts:
            cmap = await self.relation_counts(workspace_id=row.workspace_id, initiative_ids=[row.id])
            counts = cmap.get(row.id) or {
                "blocksCount": 0,
                "blockedByCount": 0,
                "relatesToCount": 0,
            }
        return serialize_initiative(
            row,
            pids,
            health_summary=summary,
            projects=projects if include_projects else None,
            relation_counts=counts,
        )

    def _empty_counts(self) -> dict:
        return {"blocksCount": 0, "blockedByCount": 0, "relatesToCount": 0}

    async def relation_counts(
        self, *, workspace_id: str, initiative_ids: list[str]
    ) -> dict[str, dict]:
        out = {iid: self._empty_counts() for iid in initiative_ids}
        if not initiative_ids:
            return out
        result = await self.db.execute(
            select(InitiativeRelation).where(
                InitiativeRelation.workspace_id == workspace_id,
                (
                    InitiativeRelation.source_initiative_id.in_(initiative_ids)
                    | InitiativeRelation.target_initiative_id.in_(initiative_ids)
                ),
            )
        )
        for rel in result.scalars().all():
            rtype = rel.relation_type
            src, tgt = rel.source_initiative_id, rel.target_initiative_id
            if rtype == "blocks":
                if src in out:
                    out[src]["blocksCount"] += 1
                if tgt in out:
                    out[tgt]["blockedByCount"] += 1
            elif rtype == "is_blocked_by":
                if src in out:
                    out[src]["blockedByCount"] += 1
                if tgt in out:
                    out[tgt]["blocksCount"] += 1
            elif rtype == "relates_to":
                if src in out:
                    out[src]["relatesToCount"] += 1
                if tgt in out:
                    out[tgt]["relatesToCount"] += 1
        return out

    async def _blocks_adjacency(self, *, workspace_id: str) -> dict[str, set[str]]:
        """Directed blocks graph: A→B means A blocks B."""
        result = await self.db.execute(
            select(InitiativeRelation).where(
                InitiativeRelation.workspace_id == workspace_id,
                InitiativeRelation.relation_type.in_(("blocks", "is_blocked_by")),
            )
        )
        adj: dict[str, set[str]] = {}
        for rel in result.scalars().all():
            if rel.relation_type == "blocks":
                src, dst = rel.source_initiative_id, rel.target_initiative_id
            else:
                # is_blocked_by: source is blocked by target ⇒ target blocks source
                src, dst = rel.target_initiative_id, rel.source_initiative_id
            adj.setdefault(src, set()).add(dst)
        return adj

    def _would_create_blocks_cycle(
        self,
        adj: dict[str, set[str]],
        *,
        edge_from: str,
        edge_to: str,
    ) -> bool:
        """True if adding edge_from→edge_to creates a directed cycle (depth cap)."""
        if edge_from == edge_to:
            return True
        # DFS from edge_to looking for edge_from
        stack = [(edge_to, 0)]
        seen: set[str] = set()
        while stack:
            node, depth = stack.pop()
            if node == edge_from:
                return True
            if depth >= _BLOCKS_CYCLE_DEPTH_CAP or node in seen:
                continue
            seen.add(node)
            for nxt in adj.get(node, ()):
                stack.append((nxt, depth + 1))
        # also account for the new edge in walk: start neighbors include edge_to via new edge
        return False

    def _serialize_relation_item(
        self,
        rel: InitiativeRelation,
        *,
        viewed_id: str,
        other: Initiative,
    ) -> dict:
        direction = "outgoing" if rel.source_initiative_id == viewed_id else "incoming"
        return {
            "id": rel.id,
            "type": rel.relation_type,
            "direction": direction,
            "initiative": {
                "id": other.id,
                "name": other.name,
                "status": other.status,
            },
        }

    async def list_relations(self, *, workspace_id: str, initiative_id: str) -> list[dict]:
        await self.get(workspace_id=workspace_id, initiative_id=initiative_id)
        result = await self.db.execute(
            select(InitiativeRelation).where(
                InitiativeRelation.workspace_id == workspace_id,
                (
                    (InitiativeRelation.source_initiative_id == initiative_id)
                    | (InitiativeRelation.target_initiative_id == initiative_id)
                ),
            )
        )
        rows = list(result.scalars().all())
        other_ids = set()
        for rel in rows:
            other_ids.add(
                rel.target_initiative_id
                if rel.source_initiative_id == initiative_id
                else rel.source_initiative_id
            )
        others: dict[str, Initiative] = {}
        if other_ids:
            ores = await self.db.execute(
                select(Initiative).where(
                    Initiative.workspace_id == workspace_id,
                    Initiative.id.in_(list(other_ids)),
                )
            )
            others = {r.id: r for r in ores.scalars().all()}
        items: list[dict] = []
        for rel in rows:
            oid = (
                rel.target_initiative_id
                if rel.source_initiative_id == initiative_id
                else rel.source_initiative_id
            )
            other = others.get(oid)
            if not other:
                continue
            items.append(self._serialize_relation_item(rel, viewed_id=initiative_id, other=other))
        return items

    async def add_relation(
        self,
        *,
        workspace_id: str,
        initiative_id: str,
        target_initiative_id: str,
        relation_type: str,
        user_id: str,
    ) -> dict:
        if relation_type not in INITIATIVE_RELATION_TYPES:
            raise HTTPException(
                status_code=http_status.HTTP_400_BAD_REQUEST,
                detail=f"非法 type，允许: {', '.join(INITIATIVE_RELATION_TYPES)}",
            )
        if initiative_id == target_initiative_id:
            raise HTTPException(
                status_code=http_status.HTTP_400_BAD_REQUEST,
                detail="不能与自身建立关系",
            )
        source = await self.get(workspace_id=workspace_id, initiative_id=initiative_id)
        target = await self.get(workspace_id=workspace_id, initiative_id=target_initiative_id)

        if relation_type in ("blocks", "is_blocked_by"):
            if relation_type == "blocks":
                edge_from, edge_to = initiative_id, target_initiative_id
            else:
                edge_from, edge_to = target_initiative_id, initiative_id
            adj = await self._blocks_adjacency(workspace_id=workspace_id)
            adj.setdefault(edge_from, set()).add(edge_to)
            if self._would_create_blocks_cycle(adj, edge_from=edge_from, edge_to=edge_to):
                raise HTTPException(
                    status_code=http_status.HTTP_400_BAD_REQUEST,
                    detail="blocks 关系将形成环",
                )

        rel = InitiativeRelation(
            workspace_id=workspace_id,
            source_initiative_id=initiative_id,
            target_initiative_id=target_initiative_id,
            relation_type=relation_type,
            created_by=user_id,
        )
        self.db.add(rel)
        try:
            await self.db.commit()
        except IntegrityError:
            await self.db.rollback()
            raise HTTPException(
                status_code=http_status.HTTP_409_CONFLICT,
                detail="关系已存在",
            )
        await self.db.refresh(rel)
        return self._serialize_relation_item(rel, viewed_id=initiative_id, other=target)

    async def remove_relation(
        self, *, workspace_id: str, initiative_id: str, relation_id: str
    ) -> None:
        await self.get(workspace_id=workspace_id, initiative_id=initiative_id)
        result = await self.db.execute(
            select(InitiativeRelation).where(
                InitiativeRelation.id == relation_id,
                InitiativeRelation.workspace_id == workspace_id,
                (
                    (InitiativeRelation.source_initiative_id == initiative_id)
                    | (InitiativeRelation.target_initiative_id == initiative_id)
                ),
            )
        )
        rel = result.scalar_one_or_none()
        if not rel:
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail="关系不存在",
            )
        await self.db.delete(rel)
        await self.db.commit()
