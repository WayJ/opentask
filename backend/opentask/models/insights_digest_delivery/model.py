"""Insights digest delivery ledger (E59) — one Inbox per user per day."""
from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Optional

from sqlalchemy import Date, DateTime, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from opentask.models.base import DBModel


def _uuid() -> str:
    return str(uuid.uuid4())


class InsightsDigestDelivery(DBModel):
    """Dedup ledger: unique (workspace_id, user_id, bucket_date)."""

    __tablename__ = "insights_digest_deliveries"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, insert_default=_uuid)
    workspace_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    bucket_date: Mapped[date] = mapped_column(Date, nullable=False)
    notification_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, insert_default=datetime.utcnow
    )

    __table_args__ = (
        UniqueConstraint(
            "workspace_id",
            "user_id",
            "bucket_date",
            name="uq_insights_digest_ws_user_day",
        ),
        Index("idx_insights_digest_ws_bucket", "workspace_id", "bucket_date"),
    )
