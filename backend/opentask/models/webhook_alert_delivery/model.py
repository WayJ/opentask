"""Webhook alert delivery dedup ledger (E57)."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from opentask.models.base import DBModel

ALERT_RULE_KINDS = ("dead_window", "auto_disable")


def _uuid() -> str:
    return str(uuid.uuid4())


def webhook_id_key(webhook_id: Optional[str]) -> str:
    """Portable unique key: empty string ≡ WS-aggregate (NULL scope)."""
    return str(webhook_id) if webhook_id else ""


class WebhookAlertDelivery(DBModel):
    """One row per (workspace, webhook_scope, rule_kind, bucket) — prevents alert spam."""

    __tablename__ = "webhook_alert_deliveries"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, insert_default=_uuid)
    workspace_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # Empty string = workspace-aggregate scope (Q6a / design webhook_id|NULL)
    webhook_id_key: Mapped[str] = mapped_column(String(36), nullable=False, insert_default="")
    webhook_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("workspace_webhooks.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    rule_kind: Mapped[str] = mapped_column(String(32), nullable=False)
    bucket: Mapped[str] = mapped_column(String(64), nullable=False)
    notification_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, insert_default=datetime.utcnow
    )

    __table_args__ = (
        UniqueConstraint(
            "workspace_id",
            "webhook_id_key",
            "rule_kind",
            "bucket",
            name="uq_webhook_alert_dedupe",
        ),
        Index("idx_webhook_alert_ws_bucket", "workspace_id", "bucket"),
    )
