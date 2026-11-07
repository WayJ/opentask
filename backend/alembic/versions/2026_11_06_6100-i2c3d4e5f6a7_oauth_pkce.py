"""Bind OAuth authorization codes to PKCE S256 challenges."""
from alembic import op
import sqlalchemy as sa

revision = "i2c3d4e5f6a7"
down_revision = "h1b2c3d4e5f6"
branch_labels = None
depends_on = None

def upgrade():
    op.add_column("oauth_authorization_codes", sa.Column("code_challenge", sa.String(43), nullable=True))

def downgrade():
    op.drop_column("oauth_authorization_codes", "code_challenge")
