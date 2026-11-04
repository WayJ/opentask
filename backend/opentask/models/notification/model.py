"""Inbox 通知模型（E3-S3）"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from opentask.models.base import DBModel


def _uuid() -> str:
    return str(uuid.uuid4())


class Notification(DBModel):
    """站内通知记录（不做邮件/IM 外发）"""

    __tablename__ = "notifications"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, insert_default=_uuid)
    workspace_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    recipient_user_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    actor_user_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    type: Mapped[str] = mapped_column(
        String(32), nullable=False, comment="assigned|commented|mentioned|project_health"
    )
    resource_type: Mapped[str] = mapped_column(
        String(32), nullable=False, insert_default="issue", comment="issue|project"
    )
    resource_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    body: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    read_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    snoozed_until: Mapped[Optional[datetime]] = mapped_column(
        DateTime, nullable=True, comment="E9-S3 Inbox snooze; NULL = not snoozed"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, insert_default=datetime.utcnow
    )

    __table_args__ = (
        Index("idx_notifications_recipient_created", "recipient_user_id", "created_at"),
        Index("idx_notifications_ws_recipient", "workspace_id", "recipient_user_id"),
        Index("idx_notifications_recipient_unread", "recipient_user_id", "read_at"),
        Index("idx_notifications_recipient_snoozed", "recipient_user_id", "snoozed_until"),
    )
