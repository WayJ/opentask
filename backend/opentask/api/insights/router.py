"""Insights API（E24 + E55）— Workspace 只读效能摘要 / CSV 导出。"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
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
    project_id: Optional[str] = Query(None, alias="projectId", description="Project 切片"),
    label_id: Optional[int] = Query(
        None, alias="labelId", description="Label(Tag) 切片；单 label"
    ),
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
        project_id=project_id,
        label_id=label_id,
    )
    return success_response(data=data)


@router.get("/export.csv")
async def insights_export_csv(
    cycle_id: Optional[str] = Query(None, alias="cycleId"),
    project_id: Optional[str] = Query(None, alias="projectId"),
    label_id: Optional[int] = Query(None, alias="labelId"),
    assignee_limit: int = Query(
        DEFAULT_ASSIGNEE_LIMIT,
        alias="assigneeLimit",
        ge=1,
        le=100,
    ),
    ctx: tuple[Workspace, WorkspaceMember, UserModel] = Depends(require_workspace_context),
    session: AsyncSession = Depends(get_session),
):
    """E55：导出 Insights 切片为 CSV（viewer+）。"""
    ws, _member, _user = ctx
    body = await InsightsService(session).export_csv(
        workspace_id=ws.id,
        cycle_id=cycle_id,
        assignee_limit=assignee_limit,
        project_id=project_id,
        label_id=label_id,
    )
    return StreamingResponse(
        iter([body]),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="insights-export.csv"'},
    )
