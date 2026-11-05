"""Project template service (E72) — payload helpers + CRUD/apply/from_project."""
from __future__ import annotations

from datetime import date, datetime, time, timedelta
from typing import Any, Optional

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from opentask.models.milestone.model import Milestone
from opentask.models.project_template.model import ProjectTemplate
from opentask.models.requirement.model import Project
from opentask.models.workspace.model import WorkspaceMember

MAX_PROJECT_TEMPLATE_MILESTONES = 30


def require_writer(member: WorkspaceMember) -> None:
    if member.role not in ("owner", "member"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="仅 member/owner 可写",
        )


def compute_milestone_target_date(
    *, base_date: date, offset_days: int | None
) -> datetime | None:
    if offset_days is None:
        return None
    return datetime.combine(base_date + timedelta(days=int(offset_days)), time.min)


def validate_project_template_payload(payload: dict | None) -> dict[str, Any]:
    raw = dict(payload or {})
    milestones_in = raw.get("milestones")
    if milestones_in is None:
        milestones_in = []
    if not isinstance(milestones_in, list):
        raise HTTPException(status_code=400, detail="milestones must be a list")
    if len(milestones_in) > MAX_PROJECT_TEMPLATE_MILESTONES:
        raise HTTPException(
            status_code=400,
            detail=f"milestones max {MAX_PROJECT_TEMPLATE_MILESTONES}",
        )
    milestones: list[dict[str, Any]] = []
    for i, item in enumerate(milestones_in):
        if not isinstance(item, dict):
            raise HTTPException(status_code=400, detail="milestone must be object")
        name = str(item.get("name") or "").strip()
        if not name:
            raise HTTPException(status_code=400, detail="milestone name required")
        entry: dict[str, Any] = {"name": name[:255]}
        if item.get("description") is not None:
            entry["description"] = item.get("description")
        pos = item.get("position")
        entry["position"] = int(pos) if pos is not None else i
        if "targetOffsetDays" in item and item.get("targetOffsetDays") is not None:
            try:
                entry["targetOffsetDays"] = int(item["targetOffsetDays"])
            except (TypeError, ValueError) as exc:
                raise HTTPException(
                    status_code=400, detail="targetOffsetDays must be int"
                ) from exc
        else:
            entry["targetOffsetDays"] = None
        milestones.append(entry)
    out: dict[str, Any] = {"milestones": milestones}
    if raw.get("description") is not None:
        out["description"] = raw.get("description")
    return out


def serialize_project_template(row: ProjectTemplate) -> dict:
    return {
        "id": row.id,
        "workspaceId": row.workspace_id,
        "name": row.name,
        "description": row.description,
        "icon": row.icon,
        "payload": row.payload or {},
        "sortOrder": row.sort_order,
        "source": row.source,
        "seedKey": row.seed_key,
        "createdBy": row.created_by,
        "createdAt": row.created_at.isoformat() if row.created_at else None,
        "updatedAt": row.updated_at.isoformat() if row.updated_at else None,
    }


def serialize_milestone_row(m: Milestone) -> dict:
    return {
        "id": m.id,
        "workspace_id": m.workspace_id,
        "project_id": m.project_id,
        "name": m.name,
        "description": m.description,
        "target_date": m.target_date.isoformat() if m.target_date else None,
        "status": m.status,
        "position": m.position,
        "created_at": m.created_at.isoformat() if m.created_at else None,
        "updated_at": m.updated_at.isoformat() if m.updated_at else None,
    }


class ProjectTemplateService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list(self, *, workspace_id: str) -> list[ProjectTemplate]:
        result = await self.db.execute(
            select(ProjectTemplate)
            .where(ProjectTemplate.workspace_id == workspace_id)
            .order_by(ProjectTemplate.sort_order.asc(), ProjectTemplate.name.asc())
        )
        return list(result.scalars().all())

    async def get(self, *, workspace_id: str, template_id: str) -> ProjectTemplate:
        result = await self.db.execute(
            select(ProjectTemplate).where(
                ProjectTemplate.id == template_id,
                ProjectTemplate.workspace_id == workspace_id,
            )
        )
        row = result.scalar_one_or_none()
        if not row:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="模板不存在")
        return row

    async def create(
        self,
        *,
        workspace_id: str,
        user_id: str,
        name: str,
        description: str | None = None,
        icon: str | None = None,
        payload: dict[str, Any] | None = None,
        sort_order: int = 0,
    ) -> ProjectTemplate:
        normalized = validate_project_template_payload(payload)
        row = ProjectTemplate(
            workspace_id=workspace_id,
            name=name.strip(),
            description=description,
            icon=icon,
            payload=normalized,
            sort_order=sort_order,
            source="custom",
            seed_key=None,
            created_by=user_id,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        self.db.add(row)
        try:
            await self.db.commit()
        except IntegrityError as e:
            await self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="模板名称已存在",
            ) from e
        await self.db.refresh(row)
        return row

    async def update(
        self,
        *,
        workspace_id: str,
        template_id: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        icon: Optional[str] = None,
        payload: Optional[dict[str, Any]] = None,
        sort_order: Optional[int] = None,
    ) -> ProjectTemplate:
        row = await self.get(workspace_id=workspace_id, template_id=template_id)
        if name is not None:
            row.name = name.strip()
        if description is not None:
            row.description = description
        if icon is not None:
            row.icon = icon
        if payload is not None:
            row.payload = validate_project_template_payload(payload)
        if sort_order is not None:
            row.sort_order = sort_order
        row.updated_at = datetime.utcnow()
        try:
            await self.db.commit()
        except IntegrityError as e:
            await self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="模板名称已存在",
            ) from e
        await self.db.refresh(row)
        return row

    async def delete(self, *, workspace_id: str, template_id: str) -> None:
        row = await self.get(workspace_id=workspace_id, template_id=template_id)
        await self.db.delete(row)
        await self.db.commit()

    async def apply(
        self,
        *,
        workspace_id: str,
        template_id: str,
        name: str,
        description: str | None = None,
        starts_at: datetime | None = None,
        user_id: str | None = None,
        dept_id: str | None = None,
    ) -> dict[str, Any]:
        tpl = await self.get(workspace_id=workspace_id, template_id=template_id)
        payload = validate_project_template_payload(tpl.payload or {})
        desc = description
        if desc is None or desc == "":
            desc = payload.get("description") or tpl.description

        project = Project(
            name=name.strip(),
            description=desc,
            dept_id=dept_id,
            workspace_id=workspace_id,
        )
        if starts_at is not None:
            sa = starts_at
            if isinstance(sa, datetime) and sa.tzinfo is not None:
                sa = sa.replace(tzinfo=None)
            project.starts_at = sa
        self.db.add(project)
        await self.db.flush()

        if starts_at is not None:
            base_date = (
                starts_at.date()
                if isinstance(starts_at, datetime)
                else date.fromisoformat(str(starts_at)[:10])
            )
        else:
            base_date = datetime.utcnow().date()

        milestones: list[Milestone] = []
        now = datetime.utcnow()
        for item in payload.get("milestones") or []:
            target = compute_milestone_target_date(
                base_date=base_date, offset_days=item.get("targetOffsetDays")
            )
            row = Milestone(
                workspace_id=workspace_id,
                project_id=project.id,
                name=item["name"],
                description=item.get("description"),
                target_date=target,
                status="planned",
                position=int(item.get("position") or 0),
                created_at=now,
                updated_at=now,
            )
            self.db.add(row)
            milestones.append(row)

        await self.db.commit()
        await self.db.refresh(project)
        for m in milestones:
            await self.db.refresh(m)

        # optional watch — mirror project create when workspace present
        if user_id:
            try:
                from opentask.services.project_watcher.service import ProjectWatcherService

                await ProjectWatcherService(self.db).watch(
                    project_id=project.id,
                    workspace_id=workspace_id,
                    user_id=str(user_id),
                )
            except Exception:
                pass

        from opentask.services.project_service import ProjectService

        resp = ProjectService(self.db).to_response(project)
        project_data = resp.model_dump() if hasattr(resp, "model_dump") else resp.dict()
        # JSON-friendly datetimes
        for key in ("created_at", "updated_at", "starts_at", "target_date", "health_updated_at"):
            val = project_data.get(key)
            if hasattr(val, "isoformat"):
                project_data[key] = val.isoformat()
        return {
            "project": project_data,
            "milestones": [serialize_milestone_row(m) for m in milestones],
        }

    async def from_project(
        self,
        *,
        workspace_id: str,
        project_id: str,
        name: str,
        description: str | None = None,
        icon: str | None = None,
        user_id: str,
    ) -> ProjectTemplate:
        result = await self.db.execute(
            select(Project).where(
                Project.id == project_id,
                Project.workspace_id == workspace_id,
            )
        )
        project = result.scalar_one_or_none()
        if not project:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="项目不存在")

        m_result = await self.db.execute(
            select(Milestone)
            .where(
                Milestone.project_id == project_id,
                Milestone.workspace_id == workspace_id,
            )
            .order_by(Milestone.position.asc(), Milestone.created_at.asc())
        )
        miles = list(m_result.scalars().all())

        if project.starts_at:
            base = project.starts_at.date()
        else:
            dated = next((m for m in miles if m.target_date), None)
            base = dated.target_date.date() if dated else datetime.utcnow().date()

        payload_miles: list[dict[str, Any]] = []
        for i, m in enumerate(miles):
            offset = None
            if m.target_date is not None:
                offset = (m.target_date.date() - base).days
            payload_miles.append(
                {
                    "name": m.name,
                    "description": m.description,
                    "position": m.position if m.position is not None else i,
                    "targetOffsetDays": offset,
                }
            )

        payload = validate_project_template_payload(
            {
                "description": description if description is not None else project.description,
                "milestones": payload_miles,
            }
        )
        return await self.create(
            workspace_id=workspace_id,
            user_id=user_id,
            name=name,
            description=description if description is not None else project.description,
            icon=icon,
            payload=payload,
            sort_order=0,
        )
