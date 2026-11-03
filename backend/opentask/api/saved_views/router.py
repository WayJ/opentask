"""Saved Views API（E4-S1）— 个人筛选/排序视图"""
from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from opentask.api.workspace.deps import require_workspace_context
from opentask.models.user.model import UserModel
from opentask.models.workspace.model import Workspace, WorkspaceMember
from opentask.repositories.base import get_session
from opentask.services.saved_view.service import SavedViewService, serialize_saved_view
from opentask.utils.response import success_response

router = APIRouter(prefix="/api/saved-views", tags=["Saved Views"])


class SavedViewCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=128)
    filter: dict[str, Any] = Field(default_factory=dict)
    sort: Optional[dict[str, Any]] = None
    display: Optional[dict[str, Any]] = None
    is_favorite: bool = False


class SavedViewUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=128)
    filter: Optional[dict[str, Any]] = None
    sort: Optional[dict[str, Any]] = None
    display: Optional[dict[str, Any]] = None
    is_favorite: Optional[bool] = None


class FavoriteBody(BaseModel):
    is_favorite: bool


@router.get("")
async def list_saved_views(
    ctx: tuple[Workspace, WorkspaceMember, UserModel] = Depends(require_workspace_context),
    session: AsyncSession = Depends(get_session),
):
    ws, _member, user = ctx
    rows = await SavedViewService(session).list_mine(
        workspace_id=ws.id, owner_user_id=str(user.id)
    )
    return success_response(data={"rows": [serialize_saved_view(r) for r in rows], "total": len(rows)})


@router.post("")
async def create_saved_view(
    body: SavedViewCreate,
    ctx: tuple[Workspace, WorkspaceMember, UserModel] = Depends(require_workspace_context),
    session: AsyncSession = Depends(get_session),
):
    ws, _member, user = ctx
    row = await SavedViewService(session).create(
        workspace_id=ws.id,
        owner_user_id=str(user.id),
        name=body.name,
        filter_json=body.filter,
        sort_json=body.sort,
        display_json=body.display,
        is_favorite=body.is_favorite,
    )
    return success_response(data=serialize_saved_view(row), message="视图已保存")


@router.get("/{view_id}")
async def get_saved_view(
    view_id: str,
    ctx: tuple[Workspace, WorkspaceMember, UserModel] = Depends(require_workspace_context),
    session: AsyncSession = Depends(get_session),
):
    ws, _member, user = ctx
    row = await SavedViewService(session).get_mine(
        view_id, workspace_id=ws.id, owner_user_id=str(user.id)
    )
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="视图不存在")
    return success_response(data=serialize_saved_view(row))


@router.patch("/{view_id}")
async def update_saved_view(
    view_id: str,
    body: SavedViewUpdate,
    ctx: tuple[Workspace, WorkspaceMember, UserModel] = Depends(require_workspace_context),
    session: AsyncSession = Depends(get_session),
):
    ws, _member, user = ctx
    svc = SavedViewService(session)
    row = await svc.get_mine(view_id, workspace_id=ws.id, owner_user_id=str(user.id))
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="视图不存在")
    row = await svc.update(
        row,
        name=body.name,
        filter_json=body.filter,
        sort_json=body.sort,
        display_json=body.display,
        is_favorite=body.is_favorite,
    )
    return success_response(data=serialize_saved_view(row), message="视图已更新")


@router.delete("/{view_id}")
async def delete_saved_view(
    view_id: str,
    ctx: tuple[Workspace, WorkspaceMember, UserModel] = Depends(require_workspace_context),
    session: AsyncSession = Depends(get_session),
):
    ws, _member, user = ctx
    svc = SavedViewService(session)
    row = await svc.get_mine(view_id, workspace_id=ws.id, owner_user_id=str(user.id))
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="视图不存在")
    await svc.delete(row)
    return success_response(data={"id": view_id}, message="视图已删除")


@router.post("/{view_id}/favorite")
async def set_favorite(
    view_id: str,
    body: FavoriteBody,
    ctx: tuple[Workspace, WorkspaceMember, UserModel] = Depends(require_workspace_context),
    session: AsyncSession = Depends(get_session),
):
    ws, _member, user = ctx
    svc = SavedViewService(session)
    row = await svc.get_mine(view_id, workspace_id=ws.id, owner_user_id=str(user.id))
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="视图不存在")
    row = await svc.update(row, is_favorite=body.is_favorite)
    return success_response(data=serialize_saved_view(row))
