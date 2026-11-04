"""Insights API（E24 + E55 + E59）— summary / export / saved reports / digest tick。"""
from __future__ import annotations

from typing import Any, List, Optional

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from opentask.api.workspace.deps import require_workspace_context
from opentask.models.user.model import UserModel
from opentask.models.workspace.model import Workspace, WorkspaceMember
from opentask.repositories.base import get_session
from opentask.services.automation.service import require_writer
from opentask.services.insights.service import (
    DEFAULT_ASSIGNEE_LIMIT,
    InsightsService,
    parse_label_ids_query,
)
from opentask.utils.response import success_response

router = APIRouter(prefix="/api/insights", tags=["Insights"])


class ReportCreateBody(BaseModel):
    name: str = Field(..., min_length=1, max_length=128)
    filters: Optional[dict[str, Any]] = None
    isDefault: bool = False


class ReportPatchBody(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=128)
    filters: Optional[dict[str, Any]] = None
    isDefault: Optional[bool] = None


@router.get("/summary")
async def insights_summary(
    cycle_id: Optional[str] = Query(None, alias="cycleId", description="Cycle ID；默认 active"),
    project_id: Optional[str] = Query(None, alias="projectId", description="Project 切片"),
    label_id: Optional[int] = Query(
        None, alias="labelId", description="Label(Tag) 切片；单 label 兼容别名"
    ),
    label_ids: Optional[List[str]] = Query(
        None, alias="labelIds", description="多 label OR；重复 query 或逗号串"
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
    ids = parse_label_ids_query(label_id=label_id, label_ids_raw=label_ids)
    data = await InsightsService(session).summary(
        workspace_id=ws.id,
        cycle_id=cycle_id,
        assignee_limit=assignee_limit,
        project_id=project_id,
        label_ids=ids,
    )
    return success_response(data=data)


@router.get("/export.csv")
async def insights_export_csv(
    cycle_id: Optional[str] = Query(None, alias="cycleId"),
    project_id: Optional[str] = Query(None, alias="projectId"),
    label_id: Optional[int] = Query(None, alias="labelId"),
    label_ids: Optional[List[str]] = Query(None, alias="labelIds"),
    assignee_limit: int = Query(
        DEFAULT_ASSIGNEE_LIMIT,
        alias="assigneeLimit",
        ge=1,
        le=100,
    ),
    ctx: tuple[Workspace, WorkspaceMember, UserModel] = Depends(require_workspace_context),
    session: AsyncSession = Depends(get_session),
):
    """E55/E59：导出 Insights 切片为 CSV（viewer+）。"""
    ws, _member, _user = ctx
    ids = parse_label_ids_query(label_id=label_id, label_ids_raw=label_ids)
    body = await InsightsService(session).export_csv(
        workspace_id=ws.id,
        cycle_id=cycle_id,
        assignee_limit=assignee_limit,
        project_id=project_id,
        label_ids=ids,
    )
    return StreamingResponse(
        iter([body]),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="insights-export.csv"'},
    )


@router.get("/reports")
async def list_insights_reports(
    ctx: tuple[Workspace, WorkspaceMember, UserModel] = Depends(require_workspace_context),
    session: AsyncSession = Depends(get_session),
):
    ws, _member, user = ctx
    rows = await InsightsService(session).list_reports(
        workspace_id=ws.id, owner_user_id=str(user.id)
    )
    return success_response(data={"rows": rows})


@router.post("/reports")
async def create_insights_report(
    body: ReportCreateBody,
    ctx: tuple[Workspace, WorkspaceMember, UserModel] = Depends(require_workspace_context),
    session: AsyncSession = Depends(get_session),
):
    ws, _member, user = ctx
    data = await InsightsService(session).create_report(
        workspace_id=ws.id,
        owner_user_id=str(user.id),
        name=body.name,
        filters=body.filters,
        is_default=body.isDefault,
    )
    return success_response(data=data, message="已创建")


@router.patch("/reports/{report_id}")
async def patch_insights_report(
    report_id: str,
    body: ReportPatchBody,
    ctx: tuple[Workspace, WorkspaceMember, UserModel] = Depends(require_workspace_context),
    session: AsyncSession = Depends(get_session),
):
    ws, _member, user = ctx
    data = await InsightsService(session).update_report(
        workspace_id=ws.id,
        owner_user_id=str(user.id),
        report_id=report_id,
        name=body.name,
        filters=body.filters,
        is_default=body.isDefault,
    )
    return success_response(data=data, message="已更新")


@router.delete("/reports/{report_id}")
async def delete_insights_report(
    report_id: str,
    ctx: tuple[Workspace, WorkspaceMember, UserModel] = Depends(require_workspace_context),
    session: AsyncSession = Depends(get_session),
):
    ws, _member, user = ctx
    await InsightsService(session).delete_report(
        workspace_id=ws.id,
        owner_user_id=str(user.id),
        report_id=report_id,
    )
    return success_response(data={"id": report_id}, message="已删除")


@router.post("/run-digest")
async def run_insights_digest(
    ctx: tuple[Workspace, WorkspaceMember, UserModel] = Depends(require_workspace_context),
    session: AsyncSession = Depends(get_session),
):
    """E59：外部 tick — insights_digest Inbox（+ 可选邮件）。对齐 E39 require_writer。"""
    ws, member, user = ctx
    require_writer(member)
    result = await InsightsService(session).run_digest(
        workspace_id=ws.id,
        actor_user_id=str(user.id),
    )
    return success_response(data=result, message="已执行")
