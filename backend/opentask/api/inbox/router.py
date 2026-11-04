"""Inbox API（E3-S3 + E9-S3 snooze）"""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from opentask.auth import authenticate
from opentask.models.user.model import UserModel
from opentask.repositories.base import get_session
from opentask.services.notification.service import NotificationService, serialize_notification
from opentask.services.workspace.service import WorkspaceService
from opentask.utils.response import success_response

router = APIRouter(prefix="/api/inbox", tags=["Inbox"])

_MAX_SNOOZE = timedelta(days=90)


class SnoozeBody(BaseModel):
    until: datetime = Field(..., description="ISO datetime; must be > now and <= now+90d")


async def _optional_workspace_id(
    x_workspace_id: Annotated[Optional[str], Header(alias="X-Workspace-Id")] = None,
    current_user: UserModel = Depends(authenticate),
    session: AsyncSession = Depends(get_session),
) -> Optional[str]:
    if not x_workspace_id:
        return None
    await WorkspaceService(session).require_member(x_workspace_id, str(current_user.id))
    return x_workspace_id


def _normalize_until(until: datetime) -> datetime:
    # strip tzinfo for naive utcnow comparisons (DB stores naive utc)
    if until.tzinfo is not None:
        until = until.replace(tzinfo=None)
    return until


@router.get("")
async def list_inbox(
    unread_only: bool = Query(False),
    include_snoozed: bool = Query(False),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: UserModel = Depends(authenticate),
    session: AsyncSession = Depends(get_session),
    workspace_id: Optional[str] = Depends(_optional_workspace_id),
):
    rows, total, unread_count = await NotificationService(session).list_for_user(
        str(current_user.id),
        workspace_id=workspace_id,
        unread_only=unread_only,
        include_snoozed=include_snoozed,
        page=page,
        page_size=page_size,
    )
    return success_response(
        data={
            "rows": [serialize_notification(r) for r in rows],
            "total": total,
            "page": page,
            "pageSize": page_size,
            "unreadCount": unread_count,
        }
    )


@router.post("/read-all")
async def mark_all_read(
    current_user: UserModel = Depends(authenticate),
    session: AsyncSession = Depends(get_session),
    workspace_id: Optional[str] = Depends(_optional_workspace_id),
):
    count = await NotificationService(session).mark_all_read(
        str(current_user.id), workspace_id=workspace_id
    )
    return success_response(data={"updated": count}, message="已全部标记已读")


@router.post("/{notification_id}/read")
async def mark_one_read(
    notification_id: str,
    current_user: UserModel = Depends(authenticate),
    session: AsyncSession = Depends(get_session),
):
    row = await NotificationService(session).mark_read(notification_id, str(current_user.id))
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="通知不存在")
    return success_response(data=serialize_notification(row), message="已标记已读")


@router.post("/{notification_id}/snooze")
async def snooze_notification(
    notification_id: str,
    body: SnoozeBody,
    current_user: UserModel = Depends(authenticate),
    session: AsyncSession = Depends(get_session),
):
    now = datetime.utcnow()
    until = _normalize_until(body.until)
    if until <= now:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="until 必须晚于当前时间")
    if until > now + _MAX_SNOOZE:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="until 不得超过 90 天")
    row = await NotificationService(session).snooze(
        notification_id, str(current_user.id), until=until
    )
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="通知不存在")
    return success_response(data=serialize_notification(row), message="已延后")


@router.post("/{notification_id}/unsnooze")
async def unsnooze_notification(
    notification_id: str,
    current_user: UserModel = Depends(authenticate),
    session: AsyncSession = Depends(get_session),
):
    row = await NotificationService(session).unsnooze(notification_id, str(current_user.id))
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="通知不存在")
    return success_response(data=serialize_notification(row), message="已取消延后")
