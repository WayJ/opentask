"""Sidebar Favorites — polymorphic pin (E8-S3); ≠ Saved View is_favorite"""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, UniqueConstraint, Index
from sqlalchemy.orm import Mapped, mapped_column

from opentask.models.base import DBModel


def _uuid() -> str:
    return str(uuid.uuid4())


TARGET_TYPES = frozenset({"project", "saved_view", "issue"})


class Favorite(DBModel):
    """Personal sidebar favorite for a project, saved view, or issue."""

    __tablename__ = "favorites"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, insert_default=_uuid)
    workspace_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    target_type: Mapped[str] = mapped_column(String(20), nullable=False)
    target_id: Mapped[str] = mapped_column(String(36), nullable=False)
    position: Mapped[int] = mapped_column(Integer, nullable=False, insert_default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, insert_default=datetime.utcnow
    )

    __table_args__ = (
        UniqueConstraint(
            "workspace_id",
            "user_id",
            "target_type",
            "target_id",
            name="uq_favorites_user_target",
        ),
        Index("ix_favorites_user_ws_pos", "user_id", "workspace_id", "position"),
    )
