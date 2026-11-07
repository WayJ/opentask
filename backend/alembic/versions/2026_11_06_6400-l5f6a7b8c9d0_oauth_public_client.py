"""Allow PKCE-bound dynamically registered public clients."""
from alembic import op
import sqlalchemy as sa

revision = "l5f6a7b8c9d0"
down_revision = "k4e5f6a7b8c9"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("oauth_clients", sa.Column("token_endpoint_auth_method", sa.String(24),
                  nullable=False, server_default="client_secret_post"))
    op.create_check_constraint("ck_oauth_public_client_dynamic", "oauth_clients",
        "token_endpoint_auth_method = 'client_secret_post' OR "
        "(token_endpoint_auth_method = 'none' AND created_by IS NULL)")


def downgrade():
    bind = op.get_bind()
    if bind.execute(sa.text("SELECT 1 FROM oauth_clients WHERE token_endpoint_auth_method = 'none' LIMIT 1")).first():
        raise RuntimeError("Remove public OAuth clients before downgrade")
    op.drop_constraint("ck_oauth_public_client_dynamic", "oauth_clients", type_="check")
    op.drop_column("oauth_clients", "token_endpoint_auth_method")
