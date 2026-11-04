"""IssueVcsLink — branch/PR links on Issue (E11). Not Requirement/PGE."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from opentask.models.base import DBModel

VCS_LINK_KINDS = ("branch", "pull_request")
VCS_LINK_STATUSES = ("open", "draft", "merged", "closed", "unknown")
VCS_PROVIDERS = ("github", "gitlab", "gitea", "manual", "custom")


def _uuid() -> str:
    return str(uuid.uuid4())


class IssueVcsLink(DBModel):
    __tablename__ = "issue_vcs_links"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, insert_default=_uuid)
    workspace_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    issue_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("issues.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    kind: Mapped[str] = mapped_column(String(32), nullable=False)
    branch_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    pr_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    provider: Mapped[str] = mapped_column(String(32), nullable=False, insert_default="manual")
    external_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, insert_default="unknown")
    repo_config_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("repo_configs.id", ondelete="SET NULL"), nullable=True
    )
    title: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    created_by: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, insert_default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, insert_default=datetime.utcnow, onupdate=datetime.utcnow
    )

    __table_args__ = (
        Index("idx_issue_vcs_links_issue_kind", "issue_id", "kind"),
    )
