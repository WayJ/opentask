"""Favorite service — sidebar pins (E8-S3)"""
from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from opentask.models.favorite.model import TARGET_TYPES, Favorite
from opentask.models.issue.model import Issue
from opentask.models.issue_saved_view.model import IssueSavedView
from opentask.models.requirement.model import Project
from opentask.models.workspace.model import WorkspaceMember
from opentask.services.project_watcher.service import ProjectWatcherService


def require_writer(member: WorkspaceMember) -> None:
    if member.role not in ("owner", "member"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="仅 member/owner 可写",
        )


class FavoriteService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def _resolve_target(
        self, *, workspace_id: str, user_id: str, target_type: str, target_id: str
    ) -> dict:
        if target_type not in TARGET_TYPES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"invalid target_type: {target_type}",
            )

        if target_type == "project":
            result = await self.db.execute(
                select(Project).where(
                    Project.id == target_id,
                    Project.workspace_id == workspace_id,
                )
            )
            project = result.scalar_one_or_none()
            if not project:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, detail="项目不存在"
                )
            return {
                "id": project.id,
                "type": "project",
                "name": project.name,
                "code": None,
            }

        if target_type == "issue":
            result = await self.db.execute(
                select(Issue).where(
                    Issue.id == target_id,
                    Issue.workspace_id == workspace_id,
                )
            )
            issue = result.scalar_one_or_none()
            if not issue:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, detail="Issue 不存在"
                )
            return {
                "id": issue.id,
                "type": "issue",
                "name": issue.title,
                "code": issue.issue_code,
            }

        # saved_view — must be in workspace and accessible (own or shared)
        result = await self.db.execute(
            select(IssueSavedView).where(
                IssueSavedView.id == target_id,
                IssueSavedView.workspace_id == workspace_id,
            )
        )
        view = result.scalar_one_or_none()
        if not view:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Saved View 不存在"
            )
        if not view.is_shared and view.owner_user_id != str(user_id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Saved View 不存在"
            )
        return {
            "id": view.id,
            "type": "saved_view",
            "name": view.name,
            "code": None,
        }

    async def _next_position(self, *, workspace_id: str, user_id: str) -> int:
        q = await self.db.execute(
            select(func.coalesce(func.max(Favorite.position), -1)).where(
                Favorite.workspace_id == workspace_id,
                Favorite.user_id == str(user_id),
            )
        )
        return int(q.scalar_one()) + 1

    def serialize(self, fav: Favorite, target: dict | None = None) -> dict:
        return {
            "id": fav.id,
            "workspaceId": fav.workspace_id,
            "userId": fav.user_id,
            "targetType": fav.target_type,
            "targetId": fav.target_id,
            "position": fav.position,
            "createdAt": fav.created_at,
            "target": target
            or {
                "id": fav.target_id,
                "type": fav.target_type,
                "name": "",
                "code": None,
            },
        }

    async def list(self, *, workspace_id: str, user_id: str) -> list[dict]:
        q = (
            select(Favorite)
            .where(
                Favorite.workspace_id == workspace_id,
                Favorite.user_id == str(user_id),
            )
            .order_by(Favorite.position.asc(), Favorite.created_at.asc())
        )
        rows = list((await self.db.execute(q)).scalars().all())
        out: list[dict] = []
        for fav in rows:
            try:
                target = await self._resolve_target(
                    workspace_id=workspace_id,
                    user_id=user_id,
                    target_type=fav.target_type,
                    target_id=fav.target_id,
                )
            except HTTPException:
                # stale pin — still list with empty name
                target = {
                    "id": fav.target_id,
                    "type": fav.target_type,
                    "name": "(已删除)",
                    "code": None,
                }
            out.append(self.serialize(fav, target))
        return out

    async def add(
        self,
        *,
        workspace_id: str,
        user_id: str,
        target_type: str,
        target_id: str,
    ) -> dict:
        target = await self._resolve_target(
            workspace_id=workspace_id,
            user_id=user_id,
            target_type=target_type,
            target_id=target_id,
        )
        existing = await self.db.execute(
            select(Favorite).where(
                Favorite.workspace_id == workspace_id,
                Favorite.user_id == str(user_id),
                Favorite.target_type == target_type,
                Favorite.target_id == target_id,
            )
        )
        row = existing.scalar_one_or_none()
        if row:
            if target_type == "project":
                await ProjectWatcherService(self.db).watch(
                    project_id=target_id,
                    workspace_id=workspace_id,
                    user_id=str(user_id),
                )
            return self.serialize(row, target)

        row = Favorite(
            workspace_id=workspace_id,
            user_id=str(user_id),
            target_type=target_type,
            target_id=target_id,
            position=await self._next_position(
                workspace_id=workspace_id, user_id=user_id
            ),
        )
        self.db.add(row)
        await self.db.commit()
        await self.db.refresh(row)

        if target_type == "project":
            await ProjectWatcherService(self.db).watch(
                project_id=target_id,
                workspace_id=workspace_id,
                user_id=str(user_id),
            )

        return self.serialize(row, target)

    async def get_owned(
        self, *, favorite_id: str, workspace_id: str, user_id: str
    ) -> Favorite:
        result = await self.db.execute(
            select(Favorite).where(
                Favorite.id == favorite_id,
                Favorite.workspace_id == workspace_id,
                Favorite.user_id == str(user_id),
            )
        )
        row = result.scalar_one_or_none()
        if not row:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="收藏不存在"
            )
        return row

    async def remove(self, *, favorite_id: str, workspace_id: str, user_id: str) -> None:
        row = await self.get_owned(
            favorite_id=favorite_id, workspace_id=workspace_id, user_id=user_id
        )
        await self.db.delete(row)
        await self.db.commit()
        # unpin does NOT unwatch (D7)

    async def reorder(
        self, *, workspace_id: str, user_id: str, ordered_ids: list[str]
    ) -> list[dict]:
        q = await self.db.execute(
            select(Favorite).where(
                Favorite.workspace_id == workspace_id,
                Favorite.user_id == str(user_id),
            )
        )
        by_id = {f.id: f for f in q.scalars().all()}
        if set(ordered_ids) != set(by_id.keys()):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="ordered_ids 必须覆盖当前全部收藏",
            )
        for idx, fid in enumerate(ordered_ids):
            by_id[fid].position = idx
        await self.db.commit()
        return await self.list(workspace_id=workspace_id, user_id=user_id)
