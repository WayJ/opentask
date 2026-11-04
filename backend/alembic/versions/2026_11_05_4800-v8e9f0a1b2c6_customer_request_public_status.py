"""E63: customer request public status token + public replies.

Revision ID: v8e9f0a1b2c6
Revises: u7d8e9f0a1b5
Create Date: 2026-11-05
"""
from __future__ import annotations

from typing import Union

import sqlalchemy as sa
from alembic import op

revision: str = "v8e9f0a1b2c6"
down_revision: Union[str, None] = "u7d8e9f0a1b5"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "customer_requests",
        sa.Column("status_token", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "customer_requests",
        sa.Column(
            "status_token_enabled",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )
    op.add_column(
        "customer_requests",
        sa.Column(
            "public_replies_enabled",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )
    op.create_index(
        "ix_customer_requests_status_token",
        "customer_requests",
        ["status_token"],
        unique=True,
    )
    op.create_table(
        "customer_request_public_replies",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column(
            "request_id",
            sa.String(length=36),
            sa.ForeignKey("customer_requests.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index(
        "idx_cr_public_replies_request",
        "customer_request_public_replies",
        ["request_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("idx_cr_public_replies_request", table_name="customer_request_public_replies")
    op.drop_table("customer_request_public_replies")
    op.drop_index("ix_customer_requests_status_token", table_name="customer_requests")
    op.drop_column("customer_requests", "public_replies_enabled")
    op.drop_column("customer_requests", "status_token_enabled")
    op.drop_column("customer_requests", "status_token")
