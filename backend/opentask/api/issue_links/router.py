"""Issue external links API (E76) — http(s) bookmarks; not attachments/VCS/relations."""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from opentask.api.workspace.deps import require_workspace_context
from opentask.models.user.model import UserModel
from opentask.models.workspace.model import Workspace, WorkspaceMember
from opentask.repositories.base import get_session
from opentask.services.issue_link.service import (
    IssueLinkService,
    require_writer,
    serialize_issue_link,
)
from opentask.utils.response import success_response

router = APIRouter(prefix="/api/issues", tags=["Issue Links"])


class IssueLinkCreate(BaseModel):
    url: str = Field(..., min_length=1, max_length=2048)
    title: Optional[str] = Field(None, max_length=255)


class IssueLinkUpdate(BaseModel):
    url: Optional[str] = Field(None, max_length=2048)
    title: Optional[str] = Field(None, max_length=255)
    position: Optional[int] = None


@router.get("/{issue_id}/links")
async def list_links(
    issue_id: str,
    ctx: tuple[Workspace, WorkspaceMember, UserModel] = Depends(require_workspace_context),
    session: AsyncSession = Depends(get_session),
):
    ws, _member, _user = ctx
    rows = await IssueLinkService(session).list_links(
        workspace_id=ws.id, issue_id=issue_id
    )
    return success_response(
        data={"rows": [serialize_issue_link(r) for r in rows], "total": len(rows)}
    )


@router.post("/{issue_id}/links")
async def create_link(
    issue_id: str,
    body: IssueLinkCreate,
    ctx: tuple[Workspace, WorkspaceMember, UserModel] = Depends(require_workspace_context),
    session: AsyncSession = Depends(get_session),
):
    ws, member, user = ctx
    require_writer(member)
    try:
        row = await IssueLinkService(session).create_link(
            workspace_id=ws.id,
            issue_id=issue_id,
            user_id=str(user.id),
            url=body.url,
            title=body.title,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return success_response(data=serialize_issue_link(row), message="已添加外链")


@router.patch("/{issue_id}/links/{link_id}")
async def update_link(
    issue_id: str,
    link_id: str,
    body: IssueLinkUpdate,
    ctx: tuple[Workspace, WorkspaceMember, UserModel] = Depends(require_workspace_context),
    session: AsyncSession = Depends(get_session),
):
    ws, member, _user = ctx
    require_writer(member)
    try:
        row = await IssueLinkService(session).update_link(
            workspace_id=ws.id,
            issue_id=issue_id,
            link_id=link_id,
            url=body.url,
            title=body.title,
            position=body.position,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return success_response(data=serialize_issue_link(row), message="已更新外链")


@router.delete("/{issue_id}/links/{link_id}")
async def delete_link(
    issue_id: str,
    link_id: str,
    ctx: tuple[Workspace, WorkspaceMember, UserModel] = Depends(require_workspace_context),
    session: AsyncSession = Depends(get_session),
):
    ws, member, user = ctx
    require_writer(member)
    await IssueLinkService(session).delete_link(
        workspace_id=ws.id,
        issue_id=issue_id,
        link_id=link_id,
        user_id=str(user.id),
    )
    return success_response(data={"id": link_id}, message="已移除外链")
