"""WorkspaceInvite 模型（E12-S2）"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from opentask.models.base import DBModel


def _uuid() -> str:
    return str(uuid.uuid4())


class WorkspaceInvite(DBModel):
    """工作区邀请（copy-link；token 仅存 sha256）"""

    __tablename__ = "workspace_invites"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, insert_default=_uuid)
    workspace_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    role: Mapped[str] = mapped_column(
        String(20), nullable=False, insert_default="member", comment="member|viewer"
    )
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        insert_default="pending",
        comment="pending|accepted|revoked|expired",
    )
    invited_by: Mapped[str] = mapped_column(String(36), nullable=False)
    accepted_by: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    accepted_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, insert_default=datetime.utcnow
    )

    __table_args__ = (
        UniqueConstraint("token_hash", name="uq_workspace_invites_token_hash"),
        Index("idx_workspace_invites_ws_status", "workspace_id", "status"),
    )
