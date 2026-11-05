"""Project members roster (E79) — display/filter only; ≠ project_watchers; no ACL."""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from opentask.models.base import DBModel


def _uuid() -> str:
    return str(uuid.uuid4())


class ProjectMember(DBModel):
    """Roster membership for a project (Linear-style members; roster-only)."""

    __tablename__ = "project_members"

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
    user_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    role: Mapped[str | None] = mapped_column(
        String(32), nullable=True, comment="Optional roster label; unused by ACL"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, insert_default=datetime.utcnow
    )

    __table_args__ = (
        UniqueConstraint("project_id", "user_id", name="uq_project_members_project_user"),
    )
