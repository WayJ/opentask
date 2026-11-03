"""个人 Saved View 模型（E4-S1）"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from opentask.models.base import DBModel


def _uuid() -> str:
    return str(uuid.uuid4())


class IssueSavedView(DBModel):
    """个人 Issue 筛选/排序视图（非 IssueCollection）"""

    __tablename__ = "issue_saved_views"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, insert_default=_uuid)
    workspace_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    owner_user_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    is_favorite: Mapped[bool] = mapped_column(Boolean, nullable=False, insert_default=False)
    filter_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, insert_default=dict)
    sort_json: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, nullable=True)
    display_json: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, insert_default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, insert_default=datetime.utcnow, onupdate=datetime.utcnow
    )

    __table_args__ = (
        Index("idx_saved_views_ws_owner", "workspace_id", "owner_user_id"),
        Index("idx_saved_views_owner_fav", "owner_user_id", "is_favorite"),
    )
