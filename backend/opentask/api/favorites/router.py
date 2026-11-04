"""Favorites API（E8-S3 侧栏收藏；≠ Saved View 星标）"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from opentask.api.workspace.deps import require_workspace_context
from opentask.models.user.model import UserModel
from opentask.models.workspace.model import Workspace, WorkspaceMember
from opentask.repositories.base import get_session
from opentask.services.favorite.service import FavoriteService, require_writer
from opentask.utils.response import success_response

router = APIRouter(prefix="/api/favorites", tags=["Favorites"])


class FavoriteCreate(BaseModel):
    target_type: str = Field(..., min_length=1, max_length=20)
    target_id: str = Field(..., min_length=1, max_length=36)


class FavoriteReorder(BaseModel):
    ordered_ids: list[str] = Field(..., min_length=0)


@router.get("")
async def list_favorites(
    ctx: tuple[Workspace, WorkspaceMember, UserModel] = Depends(require_workspace_context),
    session: AsyncSession = Depends(get_session),
):
    ws, _member, user = ctx
    rows = await FavoriteService(session).list(
        workspace_id=ws.id, user_id=str(user.id)
    )
    return success_response(data={"rows": rows, "total": len(rows)})


@router.post("")
async def add_favorite(
    body: FavoriteCreate,
    ctx: tuple[Workspace, WorkspaceMember, UserModel] = Depends(require_workspace_context),
    session: AsyncSession = Depends(get_session),
):
    ws, member, user = ctx
    require_writer(member)
    row = await FavoriteService(session).add(
        workspace_id=ws.id,
        user_id=str(user.id),
        target_type=body.target_type,
        target_id=body.target_id,
    )
    return success_response(data=row, message="已收藏到侧栏")


@router.put("/reorder")
async def reorder_favorites(
    body: FavoriteReorder,
    ctx: tuple[Workspace, WorkspaceMember, UserModel] = Depends(require_workspace_context),
    session: AsyncSession = Depends(get_session),
):
    ws, member, user = ctx
    require_writer(member)
    rows = await FavoriteService(session).reorder(
        workspace_id=ws.id,
        user_id=str(user.id),
        ordered_ids=body.ordered_ids,
    )
    return success_response(data={"rows": rows, "total": len(rows)}, message="顺序已更新")


@router.delete("/{favorite_id}")
async def remove_favorite(
    favorite_id: str,
    ctx: tuple[Workspace, WorkspaceMember, UserModel] = Depends(require_workspace_context),
    session: AsyncSession = Depends(get_session),
):
    ws, member, user = ctx
    require_writer(member)
    await FavoriteService(session).remove(
        favorite_id=favorite_id,
        workspace_id=ws.id,
        user_id=str(user.id),
    )
    return success_response(data={"id": favorite_id}, message="已从侧栏移除")
