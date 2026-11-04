"""CustomField + IssueCustomFieldValue (E25) — Linear-lite Issue custom fields."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from opentask.models.base import DBModel

FIELD_TYPES = (
    "text",
    "number",
    "single_select",
    "multi_select",
    "date",
    "boolean",
    "formula",
)


def _uuid() -> str:
    return str(uuid.uuid4())


class CustomField(DBModel):
    """Workspace-scoped Issue custom field definition."""

    __tablename__ = "custom_fields"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, insert_default=_uuid)
    workspace_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    key: Mapped[str] = mapped_column(String(64), nullable=False)
    type: Mapped[str] = mapped_column(String(32), nullable=False)
    options_json: Mapped[list[Any]] = mapped_column(
        JSON().with_variant(JSONB(), "postgresql"),
        nullable=False,
        insert_default=list,
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False, insert_default=0)
    archived_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_by: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, insert_default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, insert_default=datetime.utcnow, onupdate=datetime.utcnow
    )
    # E40 formula
    formula_expr: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    formula_result_type: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)

    __table_args__ = (
        UniqueConstraint("workspace_id", "key", name="uq_custom_fields_ws_key"),
        Index("idx_custom_fields_ws_position", "workspace_id", "position"),
    )


class IssueCustomFieldValue(DBModel):
    """Per-issue value for a CustomField (JSON typed by field.type)."""

    __tablename__ = "issue_custom_field_values"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, insert_default=_uuid)
    issue_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("issues.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    field_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("custom_fields.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    value_json: Mapped[Any] = mapped_column(
        JSON().with_variant(JSONB(), "postgresql"),
        nullable=True,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, insert_default=datetime.utcnow, onupdate=datetime.utcnow
    )

    __table_args__ = (
        UniqueConstraint("issue_id", "field_id", name="uq_issue_cf_values_issue_field"),
        Index("idx_issue_cf_values_field", "field_id"),
    )
