"""insights saved reports + digest ledger + pref (E59)

Revision ID: r4a5b6c7d8e2
Revises: q3f4a5b6c7d1
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "r4a5b6c7d8e2"
down_revision: Union[str, None] = "q3f4a5b6c7d1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())
    json_type = sa.JSON().with_variant(postgresql.JSONB(), "postgresql")

    if "notification_preferences" in tables:
        cols = {c["name"] for c in inspector.get_columns("notification_preferences")}
        if "insights_digest" not in cols:
            op.add_column(
                "notification_preferences",
                sa.Column(
                    "insights_digest",
                    sa.Boolean(),
                    nullable=False,
                    server_default=sa.text("false"),
                ),
            )

    if "insights_saved_reports" not in tables:
        op.create_table(
            "insights_saved_reports",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("workspace_id", sa.String(36), sa.ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False),
            sa.Column("owner_user_id", sa.String(36), nullable=False),
            sa.Column("name", sa.String(128), nullable=False),
            sa.Column("filters", json_type, nullable=False),
            sa.Column("is_default", sa.Boolean(), nullable=False, server_default=sa.text("false")),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
        )
        op.create_index(
            "idx_insights_reports_ws_owner",
            "insights_saved_reports",
            ["workspace_id", "owner_user_id"],
        )
        op.create_index(
            "idx_insights_reports_owner_default",
            "insights_saved_reports",
            ["owner_user_id", "is_default"],
        )

    if "insights_digest_deliveries" not in tables:
        op.create_table(
            "insights_digest_deliveries",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("workspace_id", sa.String(36), sa.ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False),
            sa.Column("user_id", sa.String(36), nullable=False),
            sa.Column("bucket_date", sa.Date(), nullable=False),
            sa.Column("notification_id", sa.String(36), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.UniqueConstraint(
                "workspace_id",
                "user_id",
                "bucket_date",
                name="uq_insights_digest_ws_user_day",
            ),
        )
        op.create_index(
            "idx_insights_digest_ws_bucket",
            "insights_digest_deliveries",
            ["workspace_id", "bucket_date"],
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())
    if "insights_digest_deliveries" in tables:
        op.drop_table("insights_digest_deliveries")
    if "insights_saved_reports" in tables:
        op.drop_table("insights_saved_reports")
    if "notification_preferences" in tables:
        cols = {c["name"] for c in inspector.get_columns("notification_preferences")}
        if "insights_digest" in cols:
            op.drop_column("notification_preferences", "insights_digest")
