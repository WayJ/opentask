"""customers + customer_requests + customer_request_issues (E22)

Revision ID: c3d4e5f6a7b1
Revises: b2c3d4e5f6a0
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "c3d4e5f6a7b1"
down_revision: Union[str, None] = "b2c3d4e5f6a0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())

    if "customers" not in tables:
        op.create_table(
            "customers",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column(
                "workspace_id",
                sa.String(36),
                sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("name", sa.String(200), nullable=False),
            sa.Column("domains", sa.JSON(), nullable=False),
            sa.Column("external_url", sa.String(500), nullable=True),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.Column("created_by", sa.String(36), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.UniqueConstraint("workspace_id", "name", name="uq_customers_ws_name"),
        )
        op.create_index("idx_customers_ws_name", "customers", ["workspace_id", "name"])
        op.create_index("ix_customers_workspace_id", "customers", ["workspace_id"])

    tables = set(sa.inspect(bind).get_table_names())
    if "customer_requests" not in tables:
        op.create_table(
            "customer_requests",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column(
                "workspace_id",
                sa.String(36),
                sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column(
                "customer_id",
                sa.String(36),
                sa.ForeignKey("customers.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("title", sa.String(255), nullable=False),
            sa.Column("body", sa.Text(), nullable=True),
            sa.Column("status", sa.String(32), nullable=False, server_default="open"),
            sa.Column("priority", sa.String(16), nullable=True),
            sa.Column("created_by", sa.String(36), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
        )
        op.create_index(
            "idx_customer_requests_ws_status",
            "customer_requests",
            ["workspace_id", "status"],
        )
        op.create_index("idx_customer_requests_customer", "customer_requests", ["customer_id"])
        op.create_index("ix_customer_requests_workspace_id", "customer_requests", ["workspace_id"])

    tables = set(sa.inspect(bind).get_table_names())
    if "customer_request_issues" not in tables:
        op.create_table(
            "customer_request_issues",
            sa.Column(
                "request_id",
                sa.String(36),
                sa.ForeignKey("customer_requests.id", ondelete="CASCADE"),
                primary_key=True,
            ),
            sa.Column(
                "issue_id",
                sa.String(36),
                sa.ForeignKey("issues.id", ondelete="CASCADE"),
                primary_key=True,
            ),
            sa.Column("created_at", sa.DateTime(), nullable=False),
        )
        op.create_index(
            "idx_customer_request_issues_issue",
            "customer_request_issues",
            ["issue_id"],
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())
    if "customer_request_issues" in tables:
        op.drop_table("customer_request_issues")
    tables = set(sa.inspect(bind).get_table_names())
    if "customer_requests" in tables:
        op.drop_table("customer_requests")
    tables = set(sa.inspect(bind).get_table_names())
    if "customers" in tables:
        op.drop_table("customers")
