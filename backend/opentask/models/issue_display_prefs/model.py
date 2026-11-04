"""个人 Issue Display 默认（E7-S3）"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, JSON, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from opentask.models.base import DBModel


def _uuid() -> str:
    return str(uuid.uuid4())


class IssueDisplayPrefs(DBModel):
    """每用户每工作区一条 Issue 列表/看板 Display 个人默认。"""

    __tablename__ = "issue_display_prefs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, insert_default=_uuid)
    workspace_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    display_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, insert_default=datetime.utcnow, onupdate=datetime.utcnow
    )

    __table_args__ = (
        UniqueConstraint("workspace_id", "user_id", name="uq_issue_display_prefs_ws_user"),
    )
