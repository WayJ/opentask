"""Public Issue Forms (E31)."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from opentask.models.base import DBModel

FORM_FIELD_TYPES = (
    "title",
    "description",
    "priority",
    "labels",
    "assignee",
    "custom_field",
    "customer_id",
)


def _uuid() -> str:
    return str(uuid.uuid4())


class IssueForm(DBModel):
    """Workspace-scoped public issue form definition."""

    __tablename__ = "issue_forms"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, insert_default=_uuid)
    workspace_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    slug: Mapped[Optional[str]] = mapped_column(String(80), nullable=True)
    token: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, insert_default=True)
    fields_json: Mapped[list[Any]] = mapped_column(
        JSON().with_variant(JSONB(), "postgresql"),
        nullable=False,
        insert_default=list,
    )
    create_customer_request: Mapped[bool] = mapped_column(
        Boolean, nullable=False, insert_default=False
    )
    enqueue_triage: Mapped[bool] = mapped_column(
        Boolean, nullable=False, insert_default=False
    )
    created_by: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, insert_default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, insert_default=datetime.utcnow, onupdate=datetime.utcnow
    )

    __table_args__ = (
        UniqueConstraint("workspace_id", "slug", name="uq_issue_forms_ws_slug"),
        Index("idx_issue_forms_ws_enabled", "workspace_id", "enabled"),
    )
