"""Project health + timeline service (E8-S2)"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from opentask.models.issue.model import Issue
from opentask.models.milestone.model import Milestone
from opentask.models.project_health.model import HEALTH_STATUSES, ProjectHealthUpdate
from opentask.models.requirement.model import Project
from opentask.models.workspace.model import WorkspaceMember
from opentask.services.milestone.service import serialize_milestone
from opentask.services.notification.service import NotificationService
from opentask.services.project_watcher.service import ProjectWatcherService


def require_writer(member: WorkspaceMember) -> None:
    if member.role not in ("owner", "member"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="仅 member/owner 可更新健康状态",
        )


_STATUS_LABEL = {
    "on_track": "进展顺利",
    "at_risk": "存在风险",
    "off_track": "偏离计划",
}


def serialize_health_update(row: ProjectHealthUpdate) -> dict:
    return {
        "id": row.id,
        "workspace_id": row.workspace_id,
        "project_id": row.project_id,
        "status": row.status,
        "note": row.note,
        "actor_user_id": row.actor_user_id,
        "created_at": row.created_at,
    }


class ProjectHealthService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_project_in_workspace(self, *, project_id: str, workspace_id: str) -> Project:
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

    async def post_update(
        self,
        *,
        project_id: str,
        workspace_id: str,
        actor_user_id: str,
        status_value: str,
        note: Optional[str] = None,
    ) -> ProjectHealthUpdate:
        if status_value not in HEALTH_STATUSES:
            raise HTTPException(status_code=400, detail="无效的健康状态")
        project = await self.get_project_in_workspace(
            project_id=project_id, workspace_id=workspace_id
        )
        now = datetime.utcnow()
        row = ProjectHealthUpdate(
            workspace_id=workspace_id,
            project_id=project_id,
            status=status_value,
            note=note,
            actor_user_id=str(actor_user_id),
            created_at=now,
        )
        self.db.add(row)
        project.health_status = status_value
        project.health_note = note
        project.health_updated_at = now
        project.health_updated_by = str(actor_user_id)
        await self.db.flush()

        label = _STATUS_LABEL.get(status_value, status_value)
        title = f"项目「{project.name}」健康状态：{label}"
        watchers = await ProjectWatcherService(self.db).user_ids(project_id=project_id)
        notif = NotificationService(self.db)
        created_any = False
        for uid in watchers:
            n = await notif.create(
                workspace_id=workspace_id,
                recipient_user_id=uid,
                actor_user_id=str(actor_user_id),
                type="project_health",
                resource_type="project",
                resource_id=project_id,
                title=title,
                body=note,
            )
            if n:
                created_any = True
        await self.db.commit()
        await self.db.refresh(row)
        return row

    async def get_health(
        self, *, project_id: str, workspace_id: str, include_history: bool = False
    ) -> dict:
        project = await self.get_project_in_workspace(
            project_id=project_id, workspace_id=workspace_id
        )
        latest = None
        if project.health_status:
            latest = {
                "status": project.health_status,
                "note": project.health_note,
                "actor_user_id": project.health_updated_by,
                "created_at": project.health_updated_at,
                "project_id": project.id,
            }
        history: list[dict] = []
        if include_history:
            q = (
                select(ProjectHealthUpdate)
                .where(
                    ProjectHealthUpdate.project_id == project_id,
                    ProjectHealthUpdate.workspace_id == workspace_id,
                )
                .order_by(ProjectHealthUpdate.created_at.desc())
                .limit(50)
            )
            rows = list((await self.db.execute(q)).scalars().all())
            history = [serialize_health_update(r) for r in rows]
            if latest is None and rows:
                latest = serialize_health_update(rows[0])
        return {"latest": latest, "history": history if include_history else []}

    async def timeline(self, *, project_id: str, workspace_id: str) -> dict:
        project = await self.get_project_in_workspace(
            project_id=project_id, workspace_id=workspace_id
        )
        ms_q = (
            select(Milestone)
            .where(
                Milestone.project_id == project_id,
                Milestone.workspace_id == workspace_id,
            )
            .order_by(Milestone.position.asc(), Milestone.created_at.asc())
        )
        milestones = list((await self.db.execute(ms_q)).scalars().all())

        issue_q = (
            select(Issue)
            .where(
                Issue.project_id == project_id,
                Issue.workspace_id == workspace_id,
                or_(Issue.due_date.is_not(None), Issue.start_date.is_not(None)),
            )
            .order_by(Issue.due_date.asc().nulls_last(), Issue.start_date.asc().nulls_last())
        )
        issues = list((await self.db.execute(issue_q)).scalars().all())

        return {
            "project": {
                "id": project.id,
                "name": project.name,
                "starts_at": project.starts_at,
                "target_date": project.target_date,
                "health_status": project.health_status,
                "health_note": project.health_note,
            },
            "milestones": [serialize_milestone(m) for m in milestones],
            "issues": [
                {
                    "id": i.id,
                    "title": i.title,
                    "issue_code": getattr(i, "issue_code", None),
                    "due_date": i.due_date,
                    "start_date": getattr(i, "start_date", None),
                    "status": i.status,
                    "milestone_id": getattr(i, "milestone_id", None),
                }
                for i in issues
            ],
        }
