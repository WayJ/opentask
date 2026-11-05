"""Activity Feed read cursors (E52 thin bell)."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from opentask.models.base import DBModel


class ActivityReadCursor(DBModel):
    """Per-user per-workspace Activity Feed watermark."""

    __tablename__ = "activity_read_cursors"

    user_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    workspace_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
        index=True,
    )
    last_seen_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    last_seen_id: Mapped[str] = mapped_column(String(36), nullable=False, default="")
