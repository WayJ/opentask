"""IssueRecurrence (E35) — Linear-lite recurring issue blueprints."""
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

RECURRENCE_INTERVALS = ("daily", "weekly", "monthly")


def _uuid() -> str:
    return str(uuid.uuid4())


class IssueRecurrence(DBModel):
    """Workspace-scoped recurring issue blueprint."""

    __tablename__ = "issue_recurrences"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, insert_default=_uuid)
    workspace_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title_template: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    priority: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    labels_json: Mapped[list[Any]] = mapped_column(
        JSON().with_variant(JSONB(), "postgresql"),
        nullable=False,
        insert_default=list,
    )
    project_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    assignee_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    custom_fields_json: Mapped[dict[str, Any]] = mapped_column(
        JSON().with_variant(JSONB(), "postgresql"),
        nullable=False,
        insert_default=dict,
    )
    interval: Mapped[str] = mapped_column(String(16), nullable=False)
    weekday: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # 0=Mon .. 6=Sun
    monthday: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # 1..31
    next_run_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, insert_default=True)
    last_issue_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    created_by: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, insert_default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, insert_default=datetime.utcnow, onupdate=datetime.utcnow
    )

    __table_args__ = (
        Index("idx_issue_recurrences_ws_enabled", "workspace_id", "enabled"),
        Index("idx_issue_recurrences_ws_next", "workspace_id", "next_run_at"),
    )
