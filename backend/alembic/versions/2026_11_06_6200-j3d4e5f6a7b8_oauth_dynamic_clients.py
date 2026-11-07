"""Allow unowned RFC 7591 dynamically registered clients."""
from alembic import op
import sqlalchemy as sa

revision = "j3d4e5f6a7b8"
down_revision = "i2c3d4e5f6a7"
branch_labels = None
depends_on = None

def upgrade():
    op.alter_column("oauth_clients", "created_by", existing_type=sa.String(36), nullable=True)

def downgrade():
    # Refuse to discard dynamically registered clients during downgrade.
    op.execute("DO $$ BEGIN IF EXISTS (SELECT 1 FROM oauth_clients WHERE created_by IS NULL) THEN RAISE EXCEPTION 'dynamic OAuth clients must be removed before downgrade'; END IF; END $$")
    op.alter_column("oauth_clients", "created_by", existing_type=sa.String(36), nullable=False)
