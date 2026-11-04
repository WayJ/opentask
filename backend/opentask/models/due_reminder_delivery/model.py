"""Due reminder delivery ledger (E39) — idempotent soon/overdue/digest."""
from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Optional

from sqlalchemy import Date, DateTime, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from opentask.models.base import DBModel

DUE_REMINDER_KINDS = ("soon", "overdue", "digest")


def _uuid() -> str:
    return str(uuid.uuid4())


def make_dedupe_key(
    *,
    kind: str,
    user_id: str,
    issue_id: Optional[str],
    bucket_date: date,
    due_date_bucket: Optional[date],
) -> str:
    """Stable unique key per design D6 / digest D5."""
    if kind == "soon":
        dd = due_date_bucket.isoformat() if due_date_bucket else ""
        return f"soon:{issue_id}:{user_id}:{dd}"
    if kind == "overdue":
        return f"overdue:{issue_id}:{user_id}:{bucket_date.isoformat()}"
    if kind == "digest":
        return f"digest:{user_id}:{bucket_date.isoformat()}"
    return f"{kind}:{issue_id}:{user_id}:{bucket_date.isoformat()}"


class DueReminderDelivery(DBModel):
    """One row per delivered (or digest) bucket — prevents double-fire."""

    __tablename__ = "due_reminder_deliveries"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, insert_default=_uuid)
    workspace_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    issue_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("issues.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    user_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    kind: Mapped[str] = mapped_column(String(16), nullable=False)
    bucket_date: Mapped[date] = mapped_column(Date, nullable=False)
    due_date_bucket: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    # Portable unique: encodes soon/overdue/digest semantics (design §A uniques).
    dedupe_key: Mapped[str] = mapped_column(String(160), nullable=False)
    notification_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, insert_default=datetime.utcnow
    )

    __table_args__ = (
        UniqueConstraint("workspace_id", "dedupe_key", name="uq_due_rem_ws_dedupe"),
        Index("idx_due_rem_ws_bucket", "workspace_id", "bucket_date"),
        Index("idx_due_rem_user_bucket", "user_id", "bucket_date"),
    )
