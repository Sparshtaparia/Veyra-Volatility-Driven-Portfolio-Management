"""Add user_id to portfolios for Supabase auth ownership.

Links each portfolio to a Supabase auth.users identity.
Nullable for backwards-compatibility with existing rows.
Authorization is enforced at the FastAPI layer, not via RLS.

Revision ID: 0005_supabase_auth
Revises: 0004_phase6_operations
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0005_supabase_auth"
down_revision: str | Sequence[str] | None = "0004_phase6_operations"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Add user_id column — nullable so existing portfolios are not broken
    op.add_column(
        "portfolios",
        sa.Column("user_id", sa.String(), nullable=True),
    )
    # Index for fast user-scoped queries
    op.create_index("ix_portfolios_user_id", "portfolios", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_portfolios_user_id", table_name="portfolios")
    op.drop_column("portfolios", "user_id")
