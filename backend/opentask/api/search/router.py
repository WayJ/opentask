"""E17: Global search API (workspace-scoped)."""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from opentask.api.workspace.deps import require_workspace_context
from opentask.models.user.model import UserModel
from opentask.models.workspace.model import Workspace, WorkspaceMember
from opentask.repositories.base import get_session
from opentask.services.search.service import SearchService
from opentask.utils.response import success_response

router = APIRouter(prefix="/api/search", tags=["Search"])


@router.get("")
async def global_search(
    q: str = Query("", description="搜索关键词"),
    limit: Optional[int] = Query(10, ge=1, le=50),
    ctx: tuple[Workspace, WorkspaceMember, UserModel] = Depends(require_workspace_context),
    session: AsyncSession = Depends(get_session),
):
    ws, _member, _user = ctx
    payload = await SearchService(session).search(
        workspace_id=ws.id, q=q, limit=int(limit or 10)
    )
    return success_response(data=payload)
