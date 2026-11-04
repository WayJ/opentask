"""Workspace outbound webhooks CRUD + HMAC delivery (E29)."""
from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import logging
import secrets
import time
import uuid
from datetime import datetime, timedelta
from typing import Any, Optional
from urllib.parse import urlparse

import httpx
from fastapi import HTTPException, status as http_status
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from opentask.models.workspace.model import WorkspaceMember
from opentask.models.workspace_webhook.model import (
    DELIVERY_LOG_LIMIT,
    WEBHOOK_EVENTS,
    WebhookDeliveryLog,
    WorkspaceWebhook,
)

logger = logging.getLogger(__name__)

DELIVERY_TIMEOUT_S = 5.0
RETRY_DELAY_S = 0.3
MAX_ATTEMPTS = 2  # sync short retries (E29)
WEBHOOK_DELIVERY_MAX_ATTEMPTS = 5  # includes first sync (E44)
RETRY_BACKOFF_MINUTES = [1, 5, 25, 120]
RUN_DUE_CAP = 100


def require_owner(member: WorkspaceMember) -> None:
    """Write gate: workspace has no separate admin role → owner only."""
    if member.role != "owner":
        raise HTTPException(
            status_code=http_status.HTTP_403_FORBIDDEN,
            detail="仅 owner 可管理 Webhook",
        )


def require_reader(member: WorkspaceMember) -> None:
    """Read gate: owner|member；viewer 403."""
    if member.role not in ("owner", "member"):
        raise HTTPException(
            status_code=http_status.HTTP_403_FORBIDDEN,
            detail="仅 member/owner 可读 Webhook",
        )


def _secret_hint(secret: str) -> str:
    if not secret:
        return ""
    return f"...{secret[-4:]}"


def serialize_webhook(
    row: WorkspaceWebhook,
    *,
    include_secret: bool = False,
    deliveries: Optional[list[dict]] = None,
) -> dict:
    data: dict[str, Any] = {
        "id": row.id,
        "workspaceId": row.workspace_id,
        "name": row.name,
        "url": row.url,
        "events": list(row.events_json or []),
        "enabled": bool(row.enabled),
        "createdBy": row.created_by,
        "secretHint": _secret_hint(row.secret),
        "createdAt": row.created_at.isoformat() if row.created_at else None,
        "updatedAt": row.updated_at.isoformat() if row.updated_at else None,
    }
    if include_secret:
        data["secret"] = row.secret
    if deliveries is not None:
        data["deliveries"] = deliveries
    return data


def serialize_delivery(row: WebhookDeliveryLog) -> dict:
    status = row.status
    if not status:
        status = "success" if row.success else "pending_retry"
    replayable = (
        status in ("pending_retry", "dead") and row.payload_json is not None
    )
    return {
        "id": row.id,
        "webhookId": row.webhook_id,
        "eventType": row.event_type,
        "success": bool(row.success),
        "statusCode": row.status_code,
        "attempt": row.attempt,
        "latencyMs": row.latency_ms,
        "error": row.error,
        "createdAt": row.created_at.isoformat() if row.created_at else None,
        "status": status,
        "nextAttemptAt": row.next_attempt_at.isoformat() if row.next_attempt_at else None,
        "deliveryId": row.delivery_id,
        "replayable": replayable,
        "maxAttempts": row.max_attempts if row.max_attempts is not None else WEBHOOK_DELIVERY_MAX_ATTEMPTS,
    }


def _backoff_minutes(attempt: int) -> int:
    """attempt is the just-completed attempt count (1-based)."""
    idx = max(0, min(attempt - 1, len(RETRY_BACKOFF_MINUTES) - 1))
    return RETRY_BACKOFF_MINUTES[idx]


def sign_body(secret: str, body: bytes) -> str:
    digest = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
    return f"sha256={digest}"


def _validate_url(url: str) -> str:
    u = (url or "").strip()
    if not u:
        raise HTTPException(status_code=400, detail="url 必填")
    parsed = urlparse(u)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        raise HTTPException(status_code=400, detail="url 须为 http(s) URL")
    if len(u) > 2048:
        raise HTTPException(status_code=400, detail="url 过长")
    return u


def _validate_events(events: list[str] | None) -> list[str]:
    if not events:
        raise HTTPException(status_code=400, detail="events 不能为空")
    cleaned: list[str] = []
    allowed = set(WEBHOOK_EVENTS)
    for e in events:
        ev = str(e).strip()
        if ev not in allowed:
            raise HTTPException(
                status_code=400,
                detail=f"未知事件: {ev}；允许: {', '.join(WEBHOOK_EVENTS)}",
            )
        if ev not in cleaned:
            cleaned.append(ev)
    if not cleaned:
        raise HTTPException(status_code=400, detail="events 不能为空")
    return cleaned


def build_event_envelope(
    *,
    event_type: str,
    workspace_id: str,
    data: dict[str, Any],
) -> dict[str, Any]:
    return {
        "id": f"evt_{uuid.uuid4().hex}",
        "type": event_type,
        "createdAt": datetime.utcnow().isoformat() + "Z",
        "workspaceId": workspace_id,
        "data": data,
    }


class WorkspaceWebhookService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list(self, *, workspace_id: str) -> list[WorkspaceWebhook]:
        stmt = (
            select(WorkspaceWebhook)
            .where(WorkspaceWebhook.workspace_id == workspace_id)
            .order_by(WorkspaceWebhook.created_at.desc())
        )
        return list((await self.db.execute(stmt)).scalars().all())

    async def get(
        self, *, workspace_id: str, webhook_id: str, with_deliveries: bool = True
    ) -> tuple[WorkspaceWebhook, list[WebhookDeliveryLog]]:
        row = await self._get_or_404(workspace_id, webhook_id)
        logs: list[WebhookDeliveryLog] = []
        if with_deliveries:
            logs = await self.list_deliveries(workspace_id=workspace_id, webhook_id=webhook_id)
        return row, logs

    async def list_deliveries(
        self, *, workspace_id: str, webhook_id: str, limit: int = 20
    ) -> list[WebhookDeliveryLog]:
        stmt = (
            select(WebhookDeliveryLog)
            .where(
                WebhookDeliveryLog.workspace_id == workspace_id,
                WebhookDeliveryLog.webhook_id == webhook_id,
            )
            .order_by(WebhookDeliveryLog.created_at.desc())
            .limit(limit)
        )
        return list((await self.db.execute(stmt)).scalars().all())

    async def create(
        self,
        *,
        workspace_id: str,
        user_id: str,
        url: str,
        events: list[str],
        name: Optional[str] = None,
        enabled: bool = True,
    ) -> WorkspaceWebhook:
        url = _validate_url(url)
        events = _validate_events(events)
        secret = secrets.token_urlsafe(32)
        row = WorkspaceWebhook(
            workspace_id=workspace_id,
            name=(name or "").strip() or None,
            url=url,
            secret=secret,
            events_json=events,
            enabled=enabled,
            created_by=user_id,
        )
        self.db.add(row)
        await self.db.commit()
        await self.db.refresh(row)
        return row

    async def update(
        self,
        *,
        workspace_id: str,
        webhook_id: str,
        url: Optional[str] = None,
        events: Optional[list[str]] = None,
        name: Optional[str] = None,
        set_name: bool = False,
        enabled: Optional[bool] = None,
    ) -> WorkspaceWebhook:
        row = await self._get_or_404(workspace_id, webhook_id)
        if url is not None:
            row.url = _validate_url(url)
        if events is not None:
            row.events_json = _validate_events(events)
        if set_name:
            row.name = (name or "").strip() or None
        if enabled is not None:
            row.enabled = bool(enabled)
        row.updated_at = datetime.utcnow()
        await self.db.commit()
        await self.db.refresh(row)
        return row

    async def delete(self, *, workspace_id: str, webhook_id: str) -> None:
        row = await self._get_or_404(workspace_id, webhook_id)
        await self.db.delete(row)
        await self.db.commit()

    async def test_deliver(
        self, *, workspace_id: str, webhook_id: str
    ) -> dict[str, Any]:
        row = await self._get_or_404(workspace_id, webhook_id)
        envelope = build_event_envelope(
            event_type="webhook.test",
            workspace_id=workspace_id,
            data={"webhookId": row.id, "message": "OpenTask webhook test"},
        )
        result = await self._deliver(row, envelope, force=True)
        return result

    async def dispatch_event(
        self,
        *,
        workspace_id: str,
        event_type: str,
        data: dict[str, Any],
    ) -> None:
        """Fan-out to all enabled hooks subscribed to event_type."""
        stmt = select(WorkspaceWebhook).where(
            WorkspaceWebhook.workspace_id == workspace_id,
            WorkspaceWebhook.enabled.is_(True),
        )
        hooks = list((await self.db.execute(stmt)).scalars().all())
        if not hooks:
            return
        envelope = build_event_envelope(
            event_type=event_type, workspace_id=workspace_id, data=data
        )
        for hook in hooks:
            events = list(hook.events_json or [])
            if event_type not in events:
                continue
            try:
                await self._deliver(hook, envelope, force=False)
            except Exception:  # noqa: BLE001
                logger.exception(
                    "webhook deliver failed hook=%s event=%s", hook.id, event_type
                )

    async def _deliver(
        self,
        hook: WorkspaceWebhook,
        envelope: dict[str, Any],
        *,
        force: bool,
        log_row: Optional[WebhookDeliveryLog] = None,
        sync_attempts: int = MAX_ATTEMPTS,
    ) -> dict[str, Any]:
        """Deliver envelope; upsert one ledger row per delivery_id.

        sync_attempts: short HTTP retries in this call (E29 default 2).
        On final failure: pending_retry (+payload) or dead when attempt>=max.
        """
        _ = force
        delivery_id = str(envelope.get("id") or f"evt_{uuid.uuid4().hex}")
        envelope = dict(envelope)
        envelope["id"] = delivery_id

        body = json.dumps(envelope, ensure_ascii=False, separators=(",", ":")).encode(
            "utf-8"
        )
        signature = sign_body(hook.secret, body)
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "OpenTask-Webhook/1.0",
            "X-OpenTask-Event": str(envelope.get("type") or ""),
            "X-OpenTask-Signature": signature,
            "X-OpenTask-Delivery": delivery_id,
        }

        log = log_row
        if log is None:
            log = await self._get_log_by_delivery(hook.id, delivery_id)
        if log is None:
            log = WebhookDeliveryLog(
                webhook_id=hook.id,
                workspace_id=hook.workspace_id,
                event_type=str(envelope.get("type") or ""),
                success=False,
                attempt=0,
                delivery_id=delivery_id,
                status="pending_retry",
                max_attempts=WEBHOOK_DELIVERY_MAX_ATTEMPTS,
            )
            self.db.add(log)
            await self.db.flush()

        starting = int(log.attempt or 0)
        max_att = int(log.max_attempts or WEBHOOK_DELIVERY_MAX_ATTEMPTS)
        last: dict[str, Any] = {
            "success": False,
            "statusCode": None,
            "attempt": starting,
            "latencyMs": None,
            "error": None,
            "eventId": delivery_id,
            "eventType": envelope.get("type"),
        }

        bursts = max(1, int(sync_attempts))
        for i in range(bursts):
            attempt = starting + i + 1
            if attempt > max_att:
                break
            if i > 0:
                await asyncio.sleep(RETRY_DELAY_S)
            last = await self._one_http(hook, body, headers, attempt=attempt)
            log.attempt = attempt
            log.status_code = last.get("statusCode")
            log.latency_ms = last.get("latencyMs")
            log.error = last.get("error")
            log.event_type = str(envelope.get("type") or log.event_type)
            log.delivery_id = delivery_id
            if last.get("success"):
                log.success = True
                log.status = (
                    "success_after_retry" if starting > 0 else "success"
                )
                log.payload_json = None
                log.next_attempt_at = None
                await self._prune_logs(hook.id)
                await self.db.commit()
                return {
                    **last,
                    "eventId": delivery_id,
                    "eventType": envelope.get("type"),
                    "status": log.status,
                }

        # failed this call
        log.success = False
        attempt_now = int(log.attempt or starting)
        if attempt_now >= max_att:
            log.status = "dead"
            log.next_attempt_at = None
            # keep payload for manual replay
            log.payload_json = envelope
        else:
            log.status = "pending_retry"
            log.payload_json = envelope
            log.next_attempt_at = datetime.utcnow() + timedelta(
                minutes=_backoff_minutes(attempt_now)
            )
        await self._prune_logs(hook.id)
        await self.db.commit()
        return {
            **last,
            "eventId": delivery_id,
            "eventType": envelope.get("type"),
            "status": log.status,
        }

    async def _one_http(
        self,
        hook: WorkspaceWebhook,
        body: bytes,
        headers: dict[str, str],
        *,
        attempt: int,
    ) -> dict[str, Any]:
        t0 = time.monotonic()
        status_code: Optional[int] = None
        error: Optional[str] = None
        success = False
        try:
            async with httpx.AsyncClient(timeout=DELIVERY_TIMEOUT_S) as client:
                resp = await client.post(hook.url, content=body, headers=headers)
                status_code = resp.status_code
                success = 200 <= resp.status_code < 300
                if not success:
                    error = (resp.text or "")[:500] or f"HTTP {resp.status_code}"
        except Exception as exc:  # noqa: BLE001
            error = str(exc)[:500]
            success = False
        latency_ms = int((time.monotonic() - t0) * 1000)
        return {
            "success": success,
            "statusCode": status_code,
            "attempt": attempt,
            "latencyMs": latency_ms,
            "error": error,
        }

    async def _get_log_by_delivery(
        self, webhook_id: str, delivery_id: str
    ) -> Optional[WebhookDeliveryLog]:
        stmt = select(WebhookDeliveryLog).where(
            WebhookDeliveryLog.webhook_id == webhook_id,
            WebhookDeliveryLog.delivery_id == delivery_id,
        )
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def _prune_logs(self, webhook_id: str) -> None:
        count_q = await self.db.execute(
            select(func.count())
            .select_from(WebhookDeliveryLog)
            .where(WebhookDeliveryLog.webhook_id == webhook_id)
        )
        total = int(count_q.scalar_one() or 0)
        if total <= DELIVERY_LOG_LIMIT:
            return
        sub = (
            select(WebhookDeliveryLog.id)
            .where(WebhookDeliveryLog.webhook_id == webhook_id)
            .order_by(WebhookDeliveryLog.created_at.asc())
            .limit(total - DELIVERY_LOG_LIMIT)
        )
        ids = list((await self.db.execute(sub)).scalars().all())
        if ids:
            await self.db.execute(
                delete(WebhookDeliveryLog).where(WebhookDeliveryLog.id.in_(ids))
            )

    async def run_due_deliveries(self, *, workspace_id: str) -> dict[str, Any]:
        now = datetime.utcnow()
        stmt = (
            select(WebhookDeliveryLog)
            .where(
                WebhookDeliveryLog.workspace_id == workspace_id,
                WebhookDeliveryLog.status == "pending_retry",
                WebhookDeliveryLog.next_attempt_at.is_not(None),
                WebhookDeliveryLog.next_attempt_at <= now,
            )
            .order_by(WebhookDeliveryLog.next_attempt_at.asc())
            .limit(RUN_DUE_CAP)
        )
        rows = list((await self.db.execute(stmt)).scalars().all())
        processed = succeeded = failed = dead = 0
        errors: list[dict[str, Any]] = []
        for log in rows:
            processed += 1
            try:
                hook = await self._get_or_404(workspace_id, log.webhook_id)
                envelope = log.payload_json
                if not isinstance(envelope, dict):
                    log.status = "dead"
                    await self.db.commit()
                    dead += 1
                    errors.append(
                        {"deliveryLogId": log.id, "error": "missing_payload"}
                    )
                    continue
                result = await self._deliver(
                    hook, dict(envelope), force=True, log_row=log, sync_attempts=1
                )
                if result.get("success"):
                    succeeded += 1
                elif result.get("status") == "dead":
                    dead += 1
                    failed += 1
                else:
                    failed += 1
            except Exception as exc:  # noqa: BLE001
                logger.exception("run-due delivery %s failed", log.id)
                failed += 1
                errors.append({"deliveryLogId": log.id, "error": str(exc)[:300]})
        return {
            "processed": processed,
            "succeeded": succeeded,
            "failed": failed,
            "dead": dead,
            "errors": errors,
        }

    async def retry_delivery(
        self,
        *,
        workspace_id: str,
        webhook_id: str,
        delivery_log_id: str,
    ) -> dict[str, Any]:
        hook = await self._get_or_404(workspace_id, webhook_id)
        stmt = select(WebhookDeliveryLog).where(
            WebhookDeliveryLog.id == delivery_log_id,
            WebhookDeliveryLog.webhook_id == webhook_id,
            WebhookDeliveryLog.workspace_id == workspace_id,
        )
        log = (await self.db.execute(stmt)).scalar_one_or_none()
        if not log:
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail="投递记录不存在",
            )
        if not isinstance(log.payload_json, dict):
            raise HTTPException(
                status_code=http_status.HTTP_400_BAD_REQUEST,
                detail="delivery_not_replayable",
            )
        # continue same delivery_id; allow beyond previous dead by bumping max if needed
        if (log.attempt or 0) >= (log.max_attempts or WEBHOOK_DELIVERY_MAX_ATTEMPTS):
            log.max_attempts = int(log.attempt or 0) + 1
        log.status = "pending_retry"
        log.next_attempt_at = None
        await self.db.flush()
        return await self._deliver(
            hook,
            dict(log.payload_json),
            force=True,
            log_row=log,
            sync_attempts=1,
        )

    async def _get_or_404(self, workspace_id: str, webhook_id: str) -> WorkspaceWebhook:
        stmt = select(WorkspaceWebhook).where(
            WorkspaceWebhook.id == webhook_id,
            WorkspaceWebhook.workspace_id == workspace_id,
        )
        row = (await self.db.execute(stmt)).scalar_one_or_none()
        if not row:
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail="Webhook 不存在",
            )
        return row


async def fire_webhooks(
    db: AsyncSession,
    *,
    workspace_id: Optional[str],
    event_type: str,
    data: Optional[dict[str, Any]] = None,
) -> None:
    """Best-effort fan-out from write paths."""
    if not workspace_id:
        return
    try:
        await WorkspaceWebhookService(db).dispatch_event(
            workspace_id=workspace_id,
            event_type=event_type,
            data=data or {},
        )
    except Exception:  # noqa: BLE001
        logger.exception("webhook fire failed event=%s", event_type)
