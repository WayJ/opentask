"""Initiative model (E10-S1) — Issue/Project axis only; no PGE."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from opentask.models.base import DBModel

INITIATIVE_STATUSES = ("planned", "active", "completed", "canceled")


def _uuid() -> str:
    return str(uuid.uuid4())


class Initiative(DBModel):
    __tablename__ = "initiatives"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, insert_default=_uuid)
    workspace_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="active")
    target_date: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    owner_user_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_by: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, insert_default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, insert_default=datetime.utcnow, onupdate=datetime.utcnow
    )

    __table_args__ = (
        UniqueConstraint("workspace_id", "name", name="uq_initiatives_ws_name"),
        Index("idx_initiatives_ws_sort", "workspace_id", "sort_order"),
        Index("idx_initiatives_ws_status", "workspace_id", "status"),
    )


class InitiativeProject(DBModel):
    __tablename__ = "initiative_projects"

    initiative_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("initiatives.id", ondelete="CASCADE"),
        primary_key=True,
    )
    project_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("projects.id", ondelete="CASCADE"),
        primary_key=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, insert_default=datetime.utcnow
    )

    __table_args__ = (
        Index("idx_initiative_projects_project", "project_id"),
    )


INITIATIVE_RELATION_TYPES = ("blocks", "is_blocked_by", "relates_to")


class InitiativeRelation(DBModel):
    """Initiative↔Initiative dependency edge (E65). Separate from issue_relations."""

    __tablename__ = "initiative_relations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, insert_default=_uuid)
    workspace_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
    )
    source_initiative_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("initiatives.id", ondelete="CASCADE"),
        nullable=False,
    )
    target_initiative_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("initiatives.id", ondelete="CASCADE"),
        nullable=False,
    )
    relation_type: Mapped[str] = mapped_column(String(32), nullable=False)
    created_by: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, insert_default=datetime.utcnow
    )

    __table_args__ = (
        UniqueConstraint(
            "source_initiative_id",
            "target_initiative_id",
            "relation_type",
            name="uq_initiative_relations_src_tgt_type",
        ),
        Index("idx_initiative_relations_ws_source", "workspace_id", "source_initiative_id"),
        Index("idx_initiative_relations_ws_target", "workspace_id", "target_initiative_id"),
    )
