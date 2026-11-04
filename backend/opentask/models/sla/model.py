"""SLA policies + issue clocks (E42)."""
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
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from opentask.models.base import DBModel

SLA_METRICS = ("time_in_status", "first_response")
CLOCK_STATUSES = ("running", "paused", "met", "breached", "cancelled")
CLOSED_STOP_STATUSES = frozenset({"resolved", "closed", "rejected"})
TARGET_MINUTES_MIN = 1
TARGET_MINUTES_MAX = 10080
DEFAULT_TARGET_MINUTES = 1440


def _uuid() -> str:
    return str(uuid.uuid4())


class SlaPolicy(DBModel):
    """Workspace-scoped time-in-status SLA policy."""

    __tablename__ = "sla_policies"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, insert_default=_uuid)
    workspace_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, insert_default=True)
    metric: Mapped[str] = mapped_column(String(32), nullable=False, insert_default="time_in_status")
    start_statuses: Mapped[list[Any]] = mapped_column(
        JSON().with_variant(JSONB(), "postgresql"),
        nullable=False,
        insert_default=list,
    )
    stop_statuses: Mapped[list[Any]] = mapped_column(
        JSON().with_variant(JSONB(), "postgresql"),
        nullable=False,
        insert_default=list,
    )
    target_minutes: Mapped[int] = mapped_column(
        Integer, nullable=False, insert_default=DEFAULT_TARGET_MINUTES
    )
    notify_assignee: Mapped[bool] = mapped_column(Boolean, nullable=False, insert_default=True)
    notify_watchers: Mapped[bool] = mapped_column(Boolean, nullable=False, insert_default=False)
    pause_statuses: Mapped[list[Any]] = mapped_column(
        JSON().with_variant(JSONB(), "postgresql"),
        nullable=False,
        insert_default=list,
    )
    # E56: optional calendar overlay {timezone?, windows?, exceptions?}; null = inherit WS
    calendar: Mapped[Optional[dict]] = mapped_column(
        JSON().with_variant(JSONB(), "postgresql"),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, insert_default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, insert_default=datetime.utcnow, onupdate=datetime.utcnow
    )

    __table_args__ = (
        Index("idx_sla_policies_ws_enabled", "workspace_id", "enabled"),
    )


class IssueSlaClock(DBModel):
    """Per-issue per-policy SLA clock row."""

    __tablename__ = "issue_sla_clocks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, insert_default=_uuid)
    workspace_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    issue_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("issues.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    policy_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("sla_policies.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    status: Mapped[str] = mapped_column(String(16), nullable=False, insert_default="running")
    started_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    deadline_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    stopped_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    breached_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    start_status: Mapped[str] = mapped_column(String(32), nullable=False)
    elapsed_before_pause_minutes: Mapped[int] = mapped_column(
        Integer, nullable=False, insert_default=0
    )
    paused_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    segment_started_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    __table_args__ = (
        Index("idx_issue_sla_clocks_ws_status_deadline", "workspace_id", "status", "deadline_at"),
        Index("idx_issue_sla_clocks_issue_policy", "issue_id", "policy_id"),
    )
