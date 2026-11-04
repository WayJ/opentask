"""Project watcher service (E8-S2)"""
from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from opentask.models.project_watcher.model import ProjectWatcher
from opentask.models.requirement.model import Project
from opentask.models.workspace.model import WorkspaceMember


def require_writer(member: WorkspaceMember) -> None:
    if member.role not in ("owner", "member"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="仅 member/owner 可写",
        )


def serialize_watcher(w: ProjectWatcher) -> dict:
    return {
        "id": w.id,
        "workspace_id": w.workspace_id,
        "project_id": w.project_id,
        "user_id": w.user_id,
        "created_at": w.created_at,
    }


class ProjectWatcherService:
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

    async def list(self, *, project_id: str, workspace_id: str) -> list[ProjectWatcher]:
        await self.get_project_in_workspace(project_id=project_id, workspace_id=workspace_id)
        q = (
            select(ProjectWatcher)
            .where(
                ProjectWatcher.project_id == project_id,
                ProjectWatcher.workspace_id == workspace_id,
            )
            .order_by(ProjectWatcher.created_at.asc())
        )
        return list((await self.db.execute(q)).scalars().all())

    async def watch(
        self, *, project_id: str, workspace_id: str, user_id: str
    ) -> ProjectWatcher:
        await self.get_project_in_workspace(project_id=project_id, workspace_id=workspace_id)
        existing = await self.db.execute(
            select(ProjectWatcher).where(
                ProjectWatcher.project_id == project_id,
                ProjectWatcher.user_id == str(user_id),
            )
        )
        row = existing.scalar_one_or_none()
        if row:
            return row
        row = ProjectWatcher(
            workspace_id=workspace_id,
            project_id=project_id,
            user_id=str(user_id),
        )
        self.db.add(row)
        await self.db.commit()
        await self.db.refresh(row)
        return row

    async def unwatch(self, *, project_id: str, workspace_id: str, user_id: str) -> None:
        await self.get_project_in_workspace(project_id=project_id, workspace_id=workspace_id)
        existing = await self.db.execute(
            select(ProjectWatcher).where(
                ProjectWatcher.project_id == project_id,
                ProjectWatcher.user_id == str(user_id),
            )
        )
        row = existing.scalar_one_or_none()
        if row:
            await self.db.delete(row)
            await self.db.commit()

    async def user_ids(self, *, project_id: str) -> list[str]:
        q = await self.db.execute(
            select(ProjectWatcher.user_id).where(ProjectWatcher.project_id == project_id)
        )
        return [str(uid) for uid in q.scalars().all()]
