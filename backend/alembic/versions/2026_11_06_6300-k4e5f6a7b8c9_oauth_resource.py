"""Bind authorization codes and refresh tokens to their requested resource."""
from alembic import op
import sqlalchemy as sa

revision = "k4e5f6a7b8c9"
down_revision = "j3d4e5f6a7b8"
branch_labels = None
depends_on = None

def upgrade():
    for table in ("oauth_authorization_codes", "oauth_refresh_tokens"):
        op.add_column(table, sa.Column("resource", sa.String(2048), nullable=True))

def downgrade():
    for table in ("oauth_authorization_codes", "oauth_refresh_tokens"):
        op.drop_column(table, "resource")
