"""E57: webhook dead-letter alert evaluation, dedup, notify, auto-disable."""
from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from opentask.models.notification.model import Notification
from opentask.models.webhook_alert_delivery.model import (
    WebhookAlertDelivery,
    webhook_id_key,
)
from opentask.models.workspace.model import Workspace, WorkspaceMember
from opentask.models.workspace_webhook.model import WebhookDeliveryLog, WorkspaceWebhook
from opentask.services.notification.service import NotificationService
from opentask.services.workspace_webhook.alert_settings import (
    DEFAULT_ALERT_SETTINGS,
    bucket_for,
    count_consecutive_dead,
    is_muted,
    merge_alert_settings,
    normalize_alert_settings,
)

logger = logging.getLogger(__name__)

PAUSED_REASON_AUTO = "auto_dead_letter_alert"
RULE_DEAD_WINDOW = "dead_window"
RULE_AUTO_DISABLE = "auto_disable"


async def _load_workspace(db: AsyncSession, workspace_id: str) -> Optional[Workspace]:
    return (
        await db.execute(select(Workspace).where(Workspace.id == workspace_id))
    ).scalar_one_or_none()


async def list_owner_user_ids(db: AsyncSession, workspace_id: str) -> list[str]:
    rows = (
        await db.execute(
            select(WorkspaceMember.user_id).where(
                WorkspaceMember.workspace_id == workspace_id,
                WorkspaceMember.role == "owner",
            )
        )
    ).scalars().all()
    return [str(u) for u in rows if u]


async def _claim_or_skip(
    db: AsyncSession,
    *,
    workspace_id: str,
    webhook_id: Optional[str],
    rule_kind: str,
    bucket: str,
) -> Optional[WebhookAlertDelivery]:
    """Check-then-insert dedup row; return row if claimed, None if already exists."""
    key = webhook_id_key(webhook_id)
    existing = (
        await db.execute(
            select(WebhookAlertDelivery).where(
                WebhookAlertDelivery.workspace_id == workspace_id,
                WebhookAlertDelivery.webhook_id_key == key,
                WebhookAlertDelivery.rule_kind == rule_kind,
                WebhookAlertDelivery.bucket == bucket,
            )
        )
    ).scalar_one_or_none()
    if existing is not None:
        return None
    row = WebhookAlertDelivery(
        workspace_id=workspace_id,
        webhook_id_key=key,
        webhook_id=webhook_id,
        rule_kind=rule_kind,
        bucket=bucket,
    )
    try:
        async with db.begin_nested():
            db.add(row)
            await db.flush()
    except IntegrityError:
        return None
    return row


async def count_dead_in_window(
    db: AsyncSession,
    *,
    workspace_id: str,
    webhook_id: Optional[str],
    window_hours: int,
    now: Optional[datetime] = None,
) -> int:
    n = now or datetime.utcnow()
    since = n - timedelta(hours=int(window_hours))
    filters = [
        WebhookDeliveryLog.workspace_id == workspace_id,
        WebhookDeliveryLog.status == "dead",
        WebhookDeliveryLog.created_at >= since,
    ]
    if webhook_id:
        filters.append(WebhookDeliveryLog.webhook_id == webhook_id)
    q = await db.execute(
        select(WebhookDeliveryLog.id).where(*filters)
    )
    return len(list(q.scalars().all()))


async def consecutive_dead_for_hook(
    db: AsyncSession,
    *,
    workspace_id: str,
    webhook_id: str,
    limit: int = 100,
) -> int:
    rows = (
        await db.execute(
            select(WebhookDeliveryLog.status)
            .where(
                WebhookDeliveryLog.workspace_id == workspace_id,
                WebhookDeliveryLog.webhook_id == webhook_id,
            )
            .order_by(
                WebhookDeliveryLog.created_at.desc(),
                WebhookDeliveryLog.id.desc(),
            )
            .limit(limit)
        )
    ).scalars().all()
    statuses = []
    for st in rows:
        if not st:
            statuses.append("pending_retry")
        else:
            statuses.append(str(st))
    return count_consecutive_dead(statuses)


async def notify_owners(
    db: AsyncSession,
    *,
    workspace_id: str,
    notif_type: str,
    resource_id: str,
    title: str,
    body: str,
) -> list[Notification]:
    """Create inbox notifications for WS owners; honors pref + E30 email. No fire_webhooks."""
    owners = await list_owner_user_ids(db, workspace_id)
    svc = NotificationService(db)
    created: list[Notification] = []
    for uid in owners:
        n = await svc.create(
            workspace_id=workspace_id,
            recipient_user_id=uid,
            actor_user_id=None,
            type=notif_type,
            resource_type="webhook",
            resource_id=resource_id,
            title=title,
            body=body,
        )
        if n:
            created.append(n)
    return created


def _ws_master_enabled(ws_settings: dict[str, Any]) -> bool:
    return bool(ws_settings.get("enabled"))


async def _evaluate_scope(
    db: AsyncSession,
    *,
    workspace_id: str,
    webhook: Optional[WorkspaceWebhook],
    ws_settings: dict[str, Any],
    effective: dict[str, Any],
    now: datetime,
    stats: dict[str, Any],
) -> None:
    """Evaluate one scope (hook or WS aggregate). WS master gate already checked."""
    if is_muted(effective, now=now):
        stats["skippedMuted"] += 1
        return
    # For hook overlay that sets enabled=False while WS master on → skip this scope
    if webhook is not None and effective.get("enabled") is False:
        # If overlay explicitly disabled OR somehow merged false
        hook_raw = getattr(webhook, "alert_settings", None)
        if isinstance(hook_raw, dict) and hook_raw.get("enabled") is False:
            stats["skippedDisabled"] += 1
            return

    window_hours = int(effective.get("windowHours") or 24)
    threshold = int(effective.get("deadThreshold") or 10)
    wid = webhook.id if webhook else None
    dead_count = await count_dead_in_window(
        db,
        workspace_id=workspace_id,
        webhook_id=wid,
        window_hours=window_hours,
        now=now,
    )
    stats["checked"] += 1

    consec = 0
    consec_thr = effective.get("consecutiveDeadThreshold")
    if webhook is not None and consec_thr is not None:
        consec = await consecutive_dead_for_hook(
            db, workspace_id=workspace_id, webhook_id=webhook.id
        )

    hit_window = dead_count >= threshold
    hit_consec = consec_thr is not None and consec >= int(consec_thr)
    if hit_window or hit_consec:
        bucket = bucket_for(window_hours, now=now)
        claimed = await _claim_or_skip(
            db,
            workspace_id=workspace_id,
            webhook_id=wid,
            rule_kind=RULE_DEAD_WINDOW,
            bucket=bucket,
        )
        if claimed is not None:
            name = (webhook.name if webhook else None) or (webhook.url if webhook else "workspace")
            title = f"Webhook 死信告警：{name}"
            body = (
                f"窗口 {window_hours}h 内 dead={dead_count}（阈值 {threshold}）"
                + (f"；连续 dead={consec}" if consec else "")
            )
            notes = await notify_owners(
                db,
                workspace_id=workspace_id,
                notif_type="webhook_dead_letter_alert",
                resource_id=wid or workspace_id,
                title=title[:255],
                body=body,
            )
            if notes:
                claimed.notification_id = notes[0].id
            stats["alerts"] += 1
            await db.commit()
        else:
            stats["dedupSkipped"] += 1

    # autoDisable — only for per-hook scope
    if webhook is None:
        return
    if not effective.get("autoDisable"):
        return
    # hard cap: prefer consecutive if set, else window threshold
    if consec_thr is not None:
        hard_hit = consec >= int(consec_thr)
    else:
        hard_hit = dead_count >= threshold
    if not hard_hit:
        return
    if not webhook.enabled and getattr(webhook, "paused_reason", None) == PAUSED_REASON_AUTO:
        return
    bucket = bucket_for(window_hours, now=now)
    claimed = await _claim_or_skip(
        db,
        workspace_id=workspace_id,
        webhook_id=webhook.id,
        rule_kind=RULE_AUTO_DISABLE,
        bucket=bucket,
    )
    if claimed is None:
        stats["dedupSkipped"] += 1
        return
    webhook.enabled = False
    webhook.paused_reason = PAUSED_REASON_AUTO
    webhook.updated_at = datetime.utcnow()
    name = webhook.name or webhook.url
    notes = await notify_owners(
        db,
        workspace_id=workspace_id,
        notif_type="webhook_auto_disabled",
        resource_id=webhook.id,
        title=f"Webhook 已自动停用：{name}"[:255],
        body=f"因死信硬顶自动停用（paused_reason={PAUSED_REASON_AUTO}）",
    )
    if notes:
        claimed.notification_id = notes[0].id
    stats["autoDisabled"] += 1
    await db.commit()


async def evaluate_webhook_alerts(
    db: AsyncSession,
    *,
    workspace_id: str,
    webhook_id: Optional[str] = None,
    now: Optional[datetime] = None,
) -> dict[str, Any]:
    """Evaluate dead-letter alerts for one hook (+ WS aggregate) or all hooks.

    Never calls fire_webhooks. Honors WS master opt-in gate (Q2a).
    """
    now = now or datetime.utcnow()
    stats: dict[str, Any] = {
        "checked": 0,
        "alerts": 0,
        "autoDisabled": 0,
        "dedupSkipped": 0,
        "skippedMuted": 0,
        "skippedDisabled": 0,
        "skippedMasterOff": 0,
    }
    ws = await _load_workspace(db, workspace_id)
    if ws is None:
        return stats
    ws_settings = normalize_alert_settings(
        getattr(ws, "webhook_alert_settings", None), partial=False
    ) or dict(DEFAULT_ALERT_SETTINGS)

    if not _ws_master_enabled(ws_settings):
        stats["skippedMasterOff"] = 1
        return stats

    hooks: list[WorkspaceWebhook] = []
    if webhook_id:
        row = (
            await db.execute(
                select(WorkspaceWebhook).where(
                    WorkspaceWebhook.id == webhook_id,
                    WorkspaceWebhook.workspace_id == workspace_id,
                )
            )
        ).scalar_one_or_none()
        if row is None:
            return stats
        hooks = [row]
    else:
        hooks = list(
            (
                await db.execute(
                    select(WorkspaceWebhook).where(
                        WorkspaceWebhook.workspace_id == workspace_id
                    )
                )
            ).scalars().all()
        )

    # per-hook scopes
    for hook in hooks:
        effective = merge_alert_settings(
            ws_settings, getattr(hook, "alert_settings", None)
        )
        # master already on; if merged enabled is False only via overlay enabled:false
        await _evaluate_scope(
            db,
            workspace_id=workspace_id,
            webhook=hook,
            ws_settings=ws_settings,
            effective=effective,
            now=now,
            stats=stats,
        )

    # WS aggregate (webhook_id=NULL)
    await _evaluate_scope(
        db,
        workspace_id=workspace_id,
        webhook=None,
        ws_settings=ws_settings,
        effective=ws_settings,
        now=now,
        stats=stats,
    )
    return stats


__all__ = [
    "PAUSED_REASON_AUTO",
    "RULE_AUTO_DISABLE",
    "RULE_DEAD_WINDOW",
    "evaluate_webhook_alerts",
    "list_owner_user_ids",
    "notify_owners",
]
