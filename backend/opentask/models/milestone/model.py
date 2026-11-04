"""Project Milestone 模型（E8-S1）"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from opentask.models.base import DBModel


def _uuid() -> str:
    return str(uuid.uuid4())


class Milestone(DBModel):
    """项目里程碑（planned | done）"""

    __tablename__ = "milestones"

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
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    target_date: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, insert_default="planned", comment="planned|done"
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False, insert_default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, insert_default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, insert_default=datetime.utcnow, onupdate=datetime.utcnow
    )

    __table_args__ = (
        Index("ix_milestones_project_position", "project_id", "position"),
    )
