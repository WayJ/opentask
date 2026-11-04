"""Tags / Tag Groups API（E7-S1）"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from opentask.api.workspace.deps import require_workspace_context
from opentask.models.user.model import UserModel
from opentask.models.workspace.model import Workspace, WorkspaceMember
from opentask.repositories.base import get_session
from opentask.services.tag.service import (
    TagService,
    require_writer,
    serialize_tag,
    serialize_tag_group,
)
from opentask.utils.response import success_response

tags_router = APIRouter(prefix="/api/tags", tags=["Tags"])
groups_router = APIRouter(prefix="/api/tag-groups", tags=["Tag Groups"])


class TagCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    color: Optional[str] = Field(None, max_length=20)
    group_id: Optional[str] = Field(None, max_length=36)


class TagUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    color: Optional[str] = Field(None, max_length=20)
    group_id: Optional[str] = Field(None, max_length=36)
    clear_group: bool = False


class TagGroupCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=64)
    color: Optional[str] = Field(None, max_length=20)
    position: int = 0


class TagGroupUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=64)
    color: Optional[str] = Field(None, max_length=20)
    position: Optional[int] = None


@tags_router.get("")
async def list_tags(
    group_id: Optional[str] = Query(None),
    q: Optional[str] = Query(None),
    ctx: tuple[Workspace, WorkspaceMember, UserModel] = Depends(require_workspace_context),
    session: AsyncSession = Depends(get_session),
):
    ws, _member, _user = ctx
    rows = await TagService(session).list_tags(
        workspace_id=ws.id, group_id=group_id, q=q
    )
    return success_response(data={"rows": [serialize_tag(r) for r in rows], "total": len(rows)})


@tags_router.post("")
async def create_tag(
    body: TagCreate,
    ctx: tuple[Workspace, WorkspaceMember, UserModel] = Depends(require_workspace_context),
    session: AsyncSession = Depends(get_session),
):
    ws, member, _user = ctx
    require_writer(member)
    row = await TagService(session).create_tag(
        workspace_id=ws.id,
        name=body.name,
        color=body.color,
        group_id=body.group_id,
    )
    return success_response(data=serialize_tag(row), message="标签已创建")


@tags_router.get("/{tag_id}")
async def get_tag(
    tag_id: int,
    ctx: tuple[Workspace, WorkspaceMember, UserModel] = Depends(require_workspace_context),
    session: AsyncSession = Depends(get_session),
):
    ws, _member, _user = ctx
    row = await TagService(session).get_tag(tag_id, workspace_id=ws.id)
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="标签不存在")
    return success_response(data=serialize_tag(row))


@tags_router.patch("/{tag_id}")
async def update_tag(
    tag_id: int,
    body: TagUpdate,
    ctx: tuple[Workspace, WorkspaceMember, UserModel] = Depends(require_workspace_context),
    session: AsyncSession = Depends(get_session),
):
    ws, member, _user = ctx
    require_writer(member)
    svc = TagService(session)
    row = await svc.get_tag(tag_id, workspace_id=ws.id)
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="标签不存在")
    row = await svc.update_tag(
        row,
        name=body.name,
        color=body.color,
        group_id=body.group_id,
        clear_group=body.clear_group,
    )
    return success_response(data=serialize_tag(row), message="标签已更新")


@tags_router.delete("/{tag_id}")
async def delete_tag(
    tag_id: int,
    ctx: tuple[Workspace, WorkspaceMember, UserModel] = Depends(require_workspace_context),
    session: AsyncSession = Depends(get_session),
):
    ws, member, _user = ctx
    require_writer(member)
    svc = TagService(session)
    row = await svc.get_tag(tag_id, workspace_id=ws.id)
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="标签不存在")
    await svc.delete_tag(row)
    return success_response(data=None, message="标签已删除")


@groups_router.get("")
async def list_tag_groups(
    ctx: tuple[Workspace, WorkspaceMember, UserModel] = Depends(require_workspace_context),
    session: AsyncSession = Depends(get_session),
):
    ws, _member, _user = ctx
    rows = await TagService(session).list_groups(workspace_id=ws.id)
    return success_response(
        data={"rows": [serialize_tag_group(r) for r in rows], "total": len(rows)}
    )


@groups_router.post("")
async def create_tag_group(
    body: TagGroupCreate,
    ctx: tuple[Workspace, WorkspaceMember, UserModel] = Depends(require_workspace_context),
    session: AsyncSession = Depends(get_session),
):
    ws, member, _user = ctx
    require_writer(member)
    row = await TagService(session).create_group(
        workspace_id=ws.id,
        name=body.name,
        color=body.color,
        position=body.position,
    )
    return success_response(data=serialize_tag_group(row), message="标签组已创建")


@groups_router.patch("/{group_id}")
async def update_tag_group(
    group_id: str,
    body: TagGroupUpdate,
    ctx: tuple[Workspace, WorkspaceMember, UserModel] = Depends(require_workspace_context),
    session: AsyncSession = Depends(get_session),
):
    ws, member, _user = ctx
    require_writer(member)
    svc = TagService(session)
    row = await svc.get_group(group_id, workspace_id=ws.id)
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="标签组不存在")
    row = await svc.update_group(
        row, name=body.name, color=body.color, position=body.position
    )
    return success_response(data=serialize_tag_group(row), message="标签组已更新")


@groups_router.delete("/{group_id}")
async def delete_tag_group(
    group_id: str,
    ctx: tuple[Workspace, WorkspaceMember, UserModel] = Depends(require_workspace_context),
    session: AsyncSession = Depends(get_session),
):
    ws, member, _user = ctx
    require_writer(member)
    svc = TagService(session)
    row = await svc.get_group(group_id, workspace_id=ws.id)
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="标签组不存在")
    await svc.delete_group(row)
    return success_response(data=None, message="标签组已删除")
