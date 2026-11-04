"""Customer + CustomerRequest models (E22) — Linear-aligned Customer Requests."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from opentask.models.base import DBModel

REQUEST_STATUSES = ("open", "completed", "canceled")
REQUEST_PRIORITIES = ("low", "medium", "high", "urgent")


def _uuid() -> str:
    return str(uuid.uuid4())


class Customer(DBModel):
    """Workspace-scoped customer (account / company)."""

    __tablename__ = "customers"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, insert_default=_uuid)
    workspace_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    domains: Mapped[list[Any]] = mapped_column(
        JSON().with_variant(JSONB(), "postgresql"),
        nullable=False,
        insert_default=list,
    )
    external_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_by: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, insert_default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, insert_default=datetime.utcnow, onupdate=datetime.utcnow
    )

    __table_args__ = (
        UniqueConstraint("workspace_id", "name", name="uq_customers_ws_name"),
        Index("idx_customers_ws_name", "workspace_id", "name"),
    )


class CustomerRequest(DBModel):
    """A need/request filed against a Customer; linkable to Issues."""

    __tablename__ = "customer_requests"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, insert_default=_uuid)
    workspace_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    customer_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("customers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    body: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="open")
    priority: Mapped[Optional[str]] = mapped_column(String(16), nullable=True)
    created_by: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, insert_default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, insert_default=datetime.utcnow, onupdate=datetime.utcnow
    )

    __table_args__ = (
        Index("idx_customer_requests_ws_status", "workspace_id", "status"),
        Index("idx_customer_requests_customer", "customer_id"),
    )


class CustomerRequestIssue(DBModel):
    """M2M link: CustomerRequest ↔ Issue (same workspace)."""

    __tablename__ = "customer_request_issues"

    request_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("customer_requests.id", ondelete="CASCADE"),
        primary_key=True,
    )
    issue_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("issues.id", ondelete="CASCADE"),
        primary_key=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, insert_default=datetime.utcnow
    )

    __table_args__ = (Index("idx_customer_request_issues_issue", "issue_id"),)
