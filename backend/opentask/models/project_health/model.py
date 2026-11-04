"""Project health update history (E8-S2)"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from opentask.models.base import DBModel


def _uuid() -> str:
    return str(uuid.uuid4())


class ProjectHealthUpdate(DBModel):
    """Immutable health status update for a project."""

    __tablename__ = "project_health_updates"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, insert_default=_uuid)
    workspace_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    project_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, comment="on_track|at_risk|off_track"
    )
    note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    actor_user_id: Mapped[str] = mapped_column(String(36), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, insert_default=datetime.utcnow
    )

    __table_args__ = (
        Index("ix_phu_project_created", "project_id", "created_at"),
    )


HEALTH_STATUSES = frozenset({"on_track", "at_risk", "off_track"})
