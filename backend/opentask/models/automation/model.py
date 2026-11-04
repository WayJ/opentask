"""AutomationRule (E26) — Linear-lite workspace workflow rules."""
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

TRIGGER_TYPES = (
    "issue.created",
    "issue.status_changed",
    "issue.assignee_changed",
    "label_added",
    "custom_field_changed",  # E36
)

ACTION_TYPES = (
    "set_status",
    "set_assignee",
    "add_label",
    "set_priority",
    "add_comment",
    "set_custom_field",  # E33
)

CF_CONDITION_OPS = (
    "eq",
    "neq",
    "contains",
    "is_set",
    "is_empty",
)


def _uuid() -> str:
    return str(uuid.uuid4())


class AutomationRule(DBModel):
    """Workspace-scoped automation rule."""

    __tablename__ = "automation_rules"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, insert_default=_uuid)
    workspace_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, insert_default=True)
    trigger_type: Mapped[str] = mapped_column(String(64), nullable=False)
    trigger_config_json: Mapped[dict[str, Any]] = mapped_column(
        JSON().with_variant(JSONB(), "postgresql"),
        nullable=False,
        insert_default=dict,
    )
    condition_json: Mapped[Optional[dict[str, Any]]] = mapped_column(
        JSON().with_variant(JSONB(), "postgresql"),
        nullable=True,
    )
    action_type: Mapped[str] = mapped_column(String(64), nullable=False)
    action_config_json: Mapped[dict[str, Any]] = mapped_column(
        JSON().with_variant(JSONB(), "postgresql"),
        nullable=False,
        insert_default=dict,
    )
    created_by: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    position: Mapped[int] = mapped_column(Integer, nullable=False, insert_default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, insert_default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, insert_default=datetime.utcnow, onupdate=datetime.utcnow
    )

    __table_args__ = (
        Index("idx_automation_rules_ws_enabled", "workspace_id", "enabled"),
        Index("idx_automation_rules_ws_trigger", "workspace_id", "trigger_type"),
        Index("idx_automation_rules_ws_position", "workspace_id", "position"),
    )


PENDING_STATUSES = ("pending", "done", "cancelled", "failed")
MAX_DELAY_MINUTES = 10080


class AutomationPendingAction(DBModel):
    """Delayed automation action queue (E38)."""

    __tablename__ = "automation_pending_actions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, insert_default=_uuid)
    workspace_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    rule_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("automation_rules.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    issue_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("issues.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    action_type: Mapped[str] = mapped_column(String(64), nullable=False)
    action_config_json: Mapped[dict[str, Any]] = mapped_column(
        JSON().with_variant(JSONB(), "postgresql"),
        nullable=False,
        insert_default=dict,
    )
    run_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, insert_default="pending")
    actor_user_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, insert_default=datetime.utcnow
    )
    executed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    __table_args__ = (
        Index("idx_auto_pending_ws_status_run", "workspace_id", "status", "run_at"),
        Index("idx_auto_pending_rule_issue_status", "rule_id", "issue_id", "status"),
    )
