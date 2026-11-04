"""Inbox API（E3-S3 + E9-S3 snooze）"""
from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from opentask.auth import authenticate
from opentask.models.user.model import UserModel
from opentask.repositories.base import get_session
from opentask.models.notification_preference.model import PREF_KEYS
from opentask.services.notification.service import NotificationService, serialize_notification
from opentask.services.email import (
    email_configured,
    resolve_recipient_email,
    send_test_email,
)
from opentask.api.workspace.deps import require_workspace_context
from opentask.models.workspace.model import Workspace, WorkspaceMember
from opentask.services.workspace.service import WorkspaceService
from opentask.services.automation.service import require_writer
from opentask.utils.response import success_response

router = APIRouter(prefix="/api/inbox", tags=["Inbox"])

_MAX_SNOOZE = timedelta(days=90)


class SnoozeBody(BaseModel):
    until: datetime = Field(..., description="ISO datetime; must be > now and <= now+90d")


class PrefsBody(BaseModel):
    issue_assigned: Optional[bool] = None
    issue_comment: Optional[bool] = None
    issue_mention: Optional[bool] = None
    issue_status: Optional[bool] = None
    due_date_changed: Optional[bool] = None
    issue_watch_event: Optional[bool] = None
    automation_comment: Optional[bool] = None
    due_reminder: Optional[bool] = None
    due_reminder_digest: Optional[bool] = None
    sla_breached: Optional[bool] = None
    webhook_delivery_alert: Optional[bool] = None
    email_enabled: Optional[bool] = None


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



@router.get("/preferences")
async def get_inbox_preferences(
    ctx: tuple[Workspace, WorkspaceMember, UserModel] = Depends(require_workspace_context),
    session: AsyncSession = Depends(get_session),
):
    """E27：当前用户在本 WS 的通知偏好（无行=全开默认）。"""
    ws, _member, user = ctx
    data = await NotificationService(session).get_prefs_payload(
        user_id=str(user.id), workspace_id=ws.id
    )
    return success_response(data=data)


@router.put("/preferences")
async def put_inbox_preferences(
    body: PrefsBody,
    ctx: tuple[Workspace, WorkspaceMember, UserModel] = Depends(require_workspace_context),
    session: AsyncSession = Depends(get_session),
):
    """E27：upsert 本人偏好；仅改传入字段。"""
    ws, _member, user = ctx
    updates = {k: getattr(body, k) for k in PREF_KEYS if hasattr(body, k) and getattr(body, k) is not None}
    if body.due_reminder_digest is not None:
        updates["due_reminder_digest"] = body.due_reminder_digest
    if body.email_enabled is not None:
        updates["email_enabled"] = body.email_enabled
    row = await NotificationService(session).upsert_prefs(
        user_id=str(user.id), workspace_id=ws.id, updates=updates
    )
    data = NotificationService(session).serialize_prefs(
        row, user_id=str(user.id), workspace_id=ws.id
    )
    return success_response(data=data, message="已保存")




@router.post("/email-test")
async def post_inbox_email_test(
    ctx: tuple[Workspace, WorkspaceMember, UserModel] = Depends(require_workspace_context),
    session: AsyncSession = Depends(get_session),
):
    """E30：向当前用户发送一封测试邮件。"""
    ws, _member, user = ctx
    if not email_configured():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="邮件未配置：请设置 SMTP_HOST 与 SMTP_FROM",
        )
    to = resolve_recipient_email(user)
    if not to:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="当前用户无可用邮箱（username 需含 @，如 user@example.com）",
        )
    try:
        ok = await send_test_email(to=to)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"发送失败: {e}",
        ) from e
    if not ok:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="邮件未配置或发送被跳过",
        )
    return success_response(data={"sent": True, "to": to}, message="测试邮件已发送")

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



@router.post("/run-due-reminders")
async def run_due_reminders(
    ctx: tuple[Workspace, WorkspaceMember, UserModel] = Depends(require_workspace_context),
    session: AsyncSession = Depends(get_session),
):
    """E39：外部 tick — soon/overdue Inbox（+ 可选 digest）。无内置 cron。"""
    ws, member, user = ctx
    require_writer(member)
    result = await NotificationService(session).run_due_reminders(
        workspace_id=ws.id,
        actor_user_id=str(user.id),
    )
    return success_response(data=result, message="已执行")


@router.get("/due-reminder-deliveries")
async def list_due_reminder_deliveries(
    bucket_date: Optional[date] = Query(None),
    limit: int = Query(100, ge=1, le=100),
    ctx: tuple[Workspace, WorkspaceMember, UserModel] = Depends(require_workspace_context),
    session: AsyncSession = Depends(get_session),
):
    """E39：投递账本只读（验收 / CLI）。"""
    ws, member, _user = ctx
    require_writer(member)
    rows = await NotificationService(session).list_due_reminder_deliveries(
        workspace_id=ws.id, bucket_date=bucket_date, limit=limit
    )
    payload = [
        {
            "id": r.id,
            "workspaceId": r.workspace_id,
            "issueId": r.issue_id,
            "userId": r.user_id,
            "kind": r.kind,
            "bucketDate": r.bucket_date.isoformat() if r.bucket_date else None,
            "dueDateBucket": r.due_date_bucket.isoformat() if r.due_date_bucket else None,
            "notificationId": r.notification_id,
            "createdAt": r.created_at,
        }
        for r in rows
    ]
    return success_response(data={"rows": payload, "total": len(payload)})


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
