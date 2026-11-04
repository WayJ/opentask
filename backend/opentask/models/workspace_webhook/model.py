"""Workspace outbound webhooks (E29)."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from opentask.models.base import DBModel

WEBHOOK_EVENTS = (
    "issue.created",
    "issue.updated",
    "issue.status_changed",
    "comment.created",
    "issue.custom_field_changed",  # E41
    "issue.sla_breached",  # E42
    "issue.assignee_changed",  # E44
    "issue.label_added",  # E44
    "issue.label_removed",  # E44
    "issue.cycle_changed",  # E51
    "issue.estimate_changed",  # E51
    "issue.project_changed",  # E51
    "issue.sla_paused",  # E51
    "issue.sla_resumed",  # E51
)

DELIVERY_LOG_LIMIT = 50


def _uuid() -> str:
    return str(uuid.uuid4())


class WorkspaceWebhook(DBModel):
    """Workspace-scoped outbound webhook endpoint."""

    __tablename__ = "workspace_webhooks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, insert_default=_uuid)
    workspace_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    url: Mapped[str] = mapped_column(String(2048), nullable=False)
    secret: Mapped[str] = mapped_column(String(128), nullable=False)
    events_json: Mapped[list[Any]] = mapped_column(
        JSON().with_variant(JSONB(), "postgresql"),
        nullable=False,
        insert_default=list,
    )
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, insert_default=True)
    alert_settings: Mapped[Optional[Any]] = mapped_column(
        JSON().with_variant(JSONB(), "postgresql"),
        nullable=True,
        comment="E57 per-hook overlay; null=inherit WS",
    )
    paused_reason: Mapped[Optional[str]] = mapped_column(
        String(64), nullable=True, comment="E57: auto_dead_letter_alert when auto-disabled"
    )
    created_by: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, insert_default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, insert_default=datetime.utcnow, onupdate=datetime.utcnow
    )

    __table_args__ = (
        Index("idx_workspace_webhooks_ws_enabled", "workspace_id", "enabled"),
    )


class WebhookDeliveryLog(DBModel):
    """Delivery ledger for a webhook (one row per logical delivery_id)."""

    __tablename__ = "webhook_delivery_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, insert_default=_uuid)
    webhook_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("workspace_webhooks.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    workspace_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    success: Mapped[bool] = mapped_column(Boolean, nullable=False, insert_default=False)
    status_code: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    attempt: Mapped[int] = mapped_column(Integer, nullable=False, insert_default=1)
    latency_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    # E44 reliability
    delivery_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    payload_json: Mapped[Optional[Any]] = mapped_column(
        JSON().with_variant(JSONB(), "postgresql"), nullable=True
    )
    status: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    next_attempt_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    max_attempts: Mapped[int] = mapped_column(Integer, nullable=False, insert_default=5)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, insert_default=datetime.utcnow
    )

    __table_args__ = (
        Index("idx_webhook_delivery_logs_hook_created", "webhook_id", "created_at"),
        Index(
            "idx_webhook_delivery_logs_ws_status_next",
            "workspace_id",
            "status",
            "next_attempt_at",
        ),
    )
