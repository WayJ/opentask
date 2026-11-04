"""EntityDocument — light Markdown notes (E10-S3). Issue/Project/Initiative only; no PGE."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from opentask.models.base import DBModel

ENTITY_DOC_PARENT_TYPES = ("issue", "project", "initiative")


def _uuid() -> str:
    return str(uuid.uuid4())


class EntityDocument(DBModel):
    __tablename__ = "entity_documents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, insert_default=_uuid)
    workspace_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    parent_type: Mapped[str] = mapped_column(String(32), nullable=False)
    parent_id: Mapped[str] = mapped_column(String(36), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    body_md: Mapped[str] = mapped_column(Text, nullable=False, default="")
    created_by: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, insert_default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, insert_default=datetime.utcnow, onupdate=datetime.utcnow
    )

    __table_args__ = (
        Index(
            "idx_entity_documents_parent",
            "workspace_id",
            "parent_type",
            "parent_id",
        ),
    )
