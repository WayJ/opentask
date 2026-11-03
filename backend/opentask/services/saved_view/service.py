"""个人 Saved View 服务（E4-S1）"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from opentask.models.issue_saved_view.model import IssueSavedView


class SavedViewService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_mine(self, *, workspace_id: str, owner_user_id: str) -> list[IssueSavedView]:
        q = (
            select(IssueSavedView)
            .where(
                IssueSavedView.workspace_id == workspace_id,
                IssueSavedView.owner_user_id == str(owner_user_id),
            )
            .order_by(
                IssueSavedView.is_favorite.desc(),
                IssueSavedView.updated_at.desc(),
            )
        )
        return list((await self.db.execute(q)).scalars().all())

    async def get_mine(
        self, view_id: str, *, workspace_id: str, owner_user_id: str
    ) -> Optional[IssueSavedView]:
        q = await self.db.execute(
            select(IssueSavedView).where(
                IssueSavedView.id == view_id,
                IssueSavedView.workspace_id == workspace_id,
                IssueSavedView.owner_user_id == str(owner_user_id),
            )
        )
        return q.scalar_one_or_none()

    async def create(
        self,
        *,
        workspace_id: str,
        owner_user_id: str,
        name: str,
        filter_json: Optional[dict[str, Any]] = None,
        sort_json: Optional[dict[str, Any]] = None,
        display_json: Optional[dict[str, Any]] = None,
        is_favorite: bool = False,
    ) -> IssueSavedView:
        now = datetime.utcnow()
        row = IssueSavedView(
            workspace_id=workspace_id,
            owner_user_id=str(owner_user_id),
            name=(name or "").strip()[:128] or "未命名视图",
            is_favorite=bool(is_favorite),
            filter_json=filter_json or {},
            sort_json=sort_json,
            display_json=display_json,
            created_at=now,
            updated_at=now,
        )
        self.db.add(row)
        await self.db.commit()
        await self.db.refresh(row)
        return row

    async def update(
        self,
        view: IssueSavedView,
        *,
        name: Optional[str] = None,
        filter_json: Optional[dict[str, Any]] = None,
        sort_json: Optional[dict[str, Any]] = None,
        display_json: Optional[dict[str, Any]] = None,
        is_favorite: Optional[bool] = None,
    ) -> IssueSavedView:
        if name is not None:
            view.name = name.strip()[:128] or view.name
        if filter_json is not None:
            view.filter_json = filter_json
        if sort_json is not None:
            view.sort_json = sort_json
        if display_json is not None:
            view.display_json = display_json
        if is_favorite is not None:
            view.is_favorite = bool(is_favorite)
        view.updated_at = datetime.utcnow()
        await self.db.commit()
        await self.db.refresh(view)
        return view

    async def delete(self, view: IssueSavedView) -> None:
        await self.db.delete(view)
        await self.db.commit()


def serialize_saved_view(v: IssueSavedView) -> dict:
    return {
        "id": v.id,
        "workspaceId": v.workspace_id,
        "ownerUserId": v.owner_user_id,
        "name": v.name,
        "isFavorite": bool(v.is_favorite),
        "filter": v.filter_json or {},
        "sort": v.sort_json,
        "display": v.display_json,
        "createdAt": v.created_at,
        "updatedAt": v.updated_at,
    }
