"""Saved View 服务（E4-S1 个人；E7-S2 工作区共享）"""
from __future__ import annotations

import copy
from datetime import datetime
from typing import Any, Optional

from fastapi import HTTPException, status
from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from opentask.models.issue_saved_view.model import IssueSavedView
from opentask.models.workspace.model import WorkspaceMember


def require_writer(member: WorkspaceMember) -> None:
    if member.role not in ("owner", "member"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="仅 member/owner 可写视图",
        )


def can_write_view(
    view: IssueSavedView, *, user_id: str, member_role: str
) -> bool:
    uid = str(user_id)
    if not view.is_shared:
        return view.owner_user_id == uid
    return view.owner_user_id == uid or member_role == "owner"


def assert_can_write_view(
    view: IssueSavedView, *, user_id: str, member_role: str
) -> None:
    if not can_write_view(view, user_id=user_id, member_role=member_role):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="无权修改此视图",
        )


class SavedViewService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_mine(self, *, workspace_id: str, owner_user_id: str) -> list[IssueSavedView]:
        """兼容：仅个人视图（is_shared=false）。"""
        q = (
            select(IssueSavedView)
            .where(
                IssueSavedView.workspace_id == workspace_id,
                IssueSavedView.owner_user_id == str(owner_user_id),
                IssueSavedView.is_shared.is_(False),
            )
            .order_by(
                IssueSavedView.is_favorite.desc(),
                IssueSavedView.updated_at.desc(),
            )
        )
        return list((await self.db.execute(q)).scalars().all())

    async def list_accessible(
        self, *, workspace_id: str, owner_user_id: str
    ) -> tuple[list[IssueSavedView], list[IssueSavedView]]:
        uid = str(owner_user_id)
        personal_q = (
            select(IssueSavedView)
            .where(
                IssueSavedView.workspace_id == workspace_id,
                IssueSavedView.owner_user_id == uid,
                IssueSavedView.is_shared.is_(False),
            )
            .order_by(
                IssueSavedView.is_favorite.desc(),
                IssueSavedView.updated_at.desc(),
            )
        )
        shared_q = (
            select(IssueSavedView)
            .where(
                IssueSavedView.workspace_id == workspace_id,
                IssueSavedView.is_shared.is_(True),
            )
            .order_by(IssueSavedView.updated_at.desc())
        )
        personal = list((await self.db.execute(personal_q)).scalars().all())
        shared = list((await self.db.execute(shared_q)).scalars().all())
        return personal, shared

    async def get_mine(
        self, view_id: str, *, workspace_id: str, owner_user_id: str
    ) -> Optional[IssueSavedView]:
        q = await self.db.execute(
            select(IssueSavedView).where(
                IssueSavedView.id == view_id,
                IssueSavedView.workspace_id == workspace_id,
                IssueSavedView.owner_user_id == str(owner_user_id),
                IssueSavedView.is_shared.is_(False),
            )
        )
        return q.scalar_one_or_none()

    async def get_accessible(
        self, view_id: str, *, workspace_id: str, owner_user_id: str
    ) -> Optional[IssueSavedView]:
        uid = str(owner_user_id)
        q = await self.db.execute(
            select(IssueSavedView).where(
                IssueSavedView.id == view_id,
                IssueSavedView.workspace_id == workspace_id,
                or_(
                    and_(
                        IssueSavedView.owner_user_id == uid,
                        IssueSavedView.is_shared.is_(False),
                    ),
                    IssueSavedView.is_shared.is_(True),
                ),
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
        is_shared: bool = False,
    ) -> IssueSavedView:
        now = datetime.utcnow()
        shared = bool(is_shared)
        # Favorite is personal-only (E7 design / E8 for shared favorites)
        favorite = False if shared else bool(is_favorite)
        row = IssueSavedView(
            workspace_id=workspace_id,
            owner_user_id=str(owner_user_id),
            name=(name or "").strip()[:128] or "未命名视图",
            is_favorite=favorite,
            is_shared=shared,
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
        is_shared: Optional[bool] = None,
    ) -> IssueSavedView:
        if name is not None:
            view.name = name.strip()[:128] or view.name
        if filter_json is not None:
            view.filter_json = filter_json
        if sort_json is not None:
            view.sort_json = sort_json
        if display_json is not None:
            view.display_json = display_json
        if is_shared is not None:
            view.is_shared = bool(is_shared)
            if view.is_shared:
                view.is_favorite = False
        if is_favorite is not None:
            if view.is_shared:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="共享视图不支持收藏",
                )
            view.is_favorite = bool(is_favorite)
        view.updated_at = datetime.utcnow()
        await self.db.commit()
        await self.db.refresh(view)
        return view

    async def delete(self, view: IssueSavedView) -> None:
        await self.db.delete(view)
        await self.db.commit()

    async def save_as(
        self,
        view: IssueSavedView,
        *,
        owner_user_id: str,
        name: Optional[str] = None,
    ) -> IssueSavedView:
        copy_name = (name or "").strip()[:128] if name else ""
        if not copy_name:
            copy_name = f"{view.name}（副本）"[:128]
        return await self.create(
            workspace_id=view.workspace_id,
            owner_user_id=str(owner_user_id),
            name=copy_name,
            filter_json=copy.deepcopy(view.filter_json or {}),
            sort_json=copy.deepcopy(view.sort_json) if view.sort_json is not None else None,
            display_json=(
                copy.deepcopy(view.display_json) if view.display_json is not None else None
            ),
            is_favorite=False,
            is_shared=False,
        )


def serialize_saved_view(v: IssueSavedView) -> dict:
    return {
        "id": v.id,
        "workspaceId": v.workspace_id,
        "ownerUserId": v.owner_user_id,
        "name": v.name,
        "isFavorite": bool(v.is_favorite),
        "isShared": bool(getattr(v, "is_shared", False)),
        "filter": v.filter_json or {},
        "sort": v.sort_json,
        "display": v.display_json,
        "createdAt": v.created_at,
        "updatedAt": v.updated_at,
    }
