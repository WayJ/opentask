"""Insights saved reports (E59 personal + E61 visibility share)."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from opentask.models.base import DBModel


def _uuid() -> str:
    return str(uuid.uuid4())


class InsightsSavedReport(DBModel):
    """Insights report preset — personal or workspace-shared (E59/E61)."""

    __tablename__ = "insights_saved_reports"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, insert_default=_uuid)
    workspace_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    owner_user_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    filters: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, insert_default=dict)
    is_default: Mapped[bool] = mapped_column(Boolean, nullable=False, insert_default=False)
    visibility: Mapped[str] = mapped_column(
        String(16), nullable=False, insert_default="personal", server_default="personal"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, insert_default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, insert_default=datetime.utcnow, onupdate=datetime.utcnow
    )

    __table_args__ = (
        Index("idx_insights_reports_ws_owner", "workspace_id", "owner_user_id"),
        Index("idx_insights_reports_owner_default", "owner_user_id", "is_default"),
        Index("idx_insights_reports_ws_visibility", "workspace_id", "visibility"),
    )
