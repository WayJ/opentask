"""E16: cleanup orphan Default Workspace seed (0 members)

Revision ID: a1b2c3d4e5f9
Revises: f6a7b8c9d0e1

The E3 tenant migration inserted
`00000000-0000-4000-8000-000000000001` ("Default Workspace") for legacy
row backfill but never seeded members. It must not appear in any user's
workspace list. Delete it when memberless; detach nullable project/issue
FKs first.
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "a1b2c3d4e5f9"
down_revision: Union[str, None] = "f6a7b8c9d0e1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

DEFAULT_WS_ID = "00000000-0000-4000-8000-000000000001"


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())
    if "workspaces" not in tables or "workspace_members" not in tables:
        return

    exists = bind.execute(
        sa.text("SELECT 1 FROM workspaces WHERE id = :id"),
        {"id": DEFAULT_WS_ID},
    ).first()
    if exists is None:
        return

    member_n = bind.execute(
        sa.text(
            "SELECT COUNT(*) FROM workspace_members WHERE workspace_id = :id"
        ),
        {"id": DEFAULT_WS_ID},
    ).scalar()
    if int(member_n or 0) > 0:
        return

    if "projects" in tables:
        bind.execute(
            sa.text(
                "UPDATE projects SET workspace_id = NULL WHERE workspace_id = :id"
            ),
            {"id": DEFAULT_WS_ID},
        )
    if "issues" in tables:
        bind.execute(
            sa.text(
                "UPDATE issues SET workspace_id = NULL WHERE workspace_id = :id"
            ),
            {"id": DEFAULT_WS_ID},
        )

    # CASCADE children (cycles, tags, …) go away with the workspace row
    bind.execute(
        sa.text("DELETE FROM workspaces WHERE id = :id"),
        {"id": DEFAULT_WS_ID},
    )


def downgrade() -> None:
    # Do not recreate the orphan seed.
    pass
