"""Display prefs API（E7-S3 + E37）"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from opentask.api.workspace.deps import require_workspace_context
from opentask.models.user.model import UserModel
from opentask.models.workspace.model import Workspace, WorkspaceMember
from opentask.repositories.base import get_session
from opentask.services.display_prefs.service import (
    DisplayPrefsService,
    serialize_display_prefs,
)
from opentask.utils.response import success_response

router = APIRouter(prefix="/api/display-prefs", tags=["Display Prefs"])


class DisplayPrefsPut(BaseModel):
    display: dict[str, Any] = Field(default_factory=dict)


@router.get("/issue")
async def get_issue_display_prefs(
    ctx: tuple[Workspace, WorkspaceMember, UserModel] = Depends(require_workspace_context),
    session: AsyncSession = Depends(get_session),
):
    ws, _member, user = ctx
    row = await DisplayPrefsService(session).get(
        workspace_id=ws.id, user_id=str(user.id)
    )
    data = await serialize_display_prefs(
        session, workspace_id=ws.id, row=row
    )
    return success_response(data=data)


@router.put("/issue")
async def put_issue_display_prefs(
    body: DisplayPrefsPut,
    ctx: tuple[Workspace, WorkspaceMember, UserModel] = Depends(require_workspace_context),
    session: AsyncSession = Depends(get_session),
):
    ws, _member, user = ctx
    row = await DisplayPrefsService(session).upsert(
        workspace_id=ws.id, user_id=str(user.id), display=body.display
    )
    data = await serialize_display_prefs(
        session, workspace_id=ws.id, row=row
    )
    return success_response(data=data)
