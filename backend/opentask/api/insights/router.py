"""Insights API（E24）— Workspace 只读效能摘要。"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from opentask.api.workspace.deps import require_workspace_context
from opentask.models.user.model import UserModel
from opentask.models.workspace.model import Workspace, WorkspaceMember
from opentask.repositories.base import get_session
from opentask.services.insights.service import DEFAULT_ASSIGNEE_LIMIT, InsightsService
from opentask.utils.response import success_response

router = APIRouter(prefix="/api/insights", tags=["Insights"])


@router.get("/summary")
async def insights_summary(
    cycle_id: Optional[str] = Query(None, alias="cycleId", description="Cycle ID；默认 active"),
    assignee_limit: int = Query(
        DEFAULT_ASSIGNEE_LIMIT,
        alias="assigneeLimit",
        ge=1,
        le=100,
        description="具名负责人 top N",
    ),
    ctx: tuple[Workspace, WorkspaceMember, UserModel] = Depends(require_workspace_context),
    session: AsyncSession = Depends(get_session),
):
    ws, _member, _user = ctx
    data = await InsightsService(session).summary(
        workspace_id=ws.id,
        cycle_id=cycle_id,
        assignee_limit=assignee_limit,
    )
    return success_response(data=data)
