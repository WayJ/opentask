"""NotificationPreference (E27) — per-user per-workspace inbox prefs."""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from opentask.models.base import DBModel

PREF_KEYS = (
    "issue_assigned",
    "issue_comment",
    "issue_mention",
    "issue_status",
    "due_date_changed",
    "issue_watch_event",
    "automation_comment",
)

# Inbox Notification.type → preference column
TYPE_TO_PREF_KEY: dict[str, str] = {
    "assigned": "issue_assigned",
    "commented": "issue_comment",
    "mentioned": "issue_mention",
    "status_changed": "issue_status",
    "due_date_changed": "due_date_changed",
    "subscribed_update": "issue_watch_event",
    "automation_comment": "automation_comment",
}


def _uuid() -> str:
    return str(uuid.uuid4())


class NotificationPreference(DBModel):
    """Per-user notification toggles scoped to a workspace."""

    __tablename__ = "notification_preferences"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, insert_default=_uuid)
    user_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    workspace_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    issue_assigned: Mapped[bool] = mapped_column(Boolean, nullable=False, insert_default=True)
    issue_comment: Mapped[bool] = mapped_column(Boolean, nullable=False, insert_default=True)
    issue_mention: Mapped[bool] = mapped_column(Boolean, nullable=False, insert_default=True)
    issue_status: Mapped[bool] = mapped_column(Boolean, nullable=False, insert_default=True)
    due_date_changed: Mapped[bool] = mapped_column(Boolean, nullable=False, insert_default=True)
    issue_watch_event: Mapped[bool] = mapped_column(Boolean, nullable=False, insert_default=True)
    automation_comment: Mapped[bool] = mapped_column(Boolean, nullable=False, insert_default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, insert_default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, insert_default=datetime.utcnow, onupdate=datetime.utcnow
    )

    __table_args__ = (
        UniqueConstraint("user_id", "workspace_id", name="uq_notif_prefs_user_ws"),
        Index("idx_notif_prefs_ws_user", "workspace_id", "user_id"),
    )
