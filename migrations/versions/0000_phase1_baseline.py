"""Bootstrap the pre-Alembic Phase 1 schema on fresh databases.

Revision ID: 0000_phase1_baseline
Revises: None
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0000_phase1_baseline"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create Phase 1 tables only when this is a genuinely fresh schema."""
    existing_tables = set(sa.inspect(op.get_bind()).get_table_names())

    if "portfolios" not in existing_tables:
        op.create_table(
            "portfolios",
            sa.Column("id", sa.String(), nullable=False),
            sa.Column("name", sa.String(), nullable=False),
            sa.Column("total_value", sa.Float(), nullable=False),
            sa.Column("currency", sa.String(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.CheckConstraint("total_value >= 0", name="check_portfolio_total_value_non_negative"),
            sa.PrimaryKeyConstraint("id"),
        )

    if "holdings" not in existing_tables:
        op.create_table(
            "holdings",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("portfolio_id", sa.String(), nullable=False),
            sa.Column("ticker", sa.String(), nullable=False),
            sa.Column("quantity", sa.Float(), nullable=False),
            sa.Column("average_price", sa.Float(), nullable=False),
            sa.Column("current_price", sa.Float(), nullable=False),
            sa.Column("market_value", sa.Float(), nullable=False),
            sa.Column("weight", sa.Float(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.CheckConstraint("quantity >= 0", name="check_holding_quantity_non_negative"),
            sa.CheckConstraint(
                "average_price >= 0", name="check_holding_average_price_non_negative"
            ),
            sa.CheckConstraint(
                "current_price >= 0", name="check_holding_current_price_non_negative"
            ),
            sa.CheckConstraint("market_value >= 0", name="check_holding_market_value_non_negative"),
            sa.CheckConstraint("weight >= 0 AND weight <= 1", name="check_holding_weight_bounds"),
            sa.ForeignKeyConstraint(["portfolio_id"], ["portfolios.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )

    if "evaluations" not in existing_tables:
        op.create_table(
            "evaluations",
            sa.Column("evaluation_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("portfolio_id", sa.String(), nullable=False),
            sa.Column("evaluation_date", sa.Date(), nullable=False),
            sa.Column(
                "trigger",
                sa.Enum("SCHEDULED", "EVENT_DRIVEN", "MANUAL", name="evaluationtrigger"),
                nullable=False,
            ),
            sa.Column(
                "decision", sa.Enum("HOLD", "REBALANCE", name="evaluationdecision"), nullable=False
            ),
            sa.Column(
                "status",
                sa.Enum("PENDING", "COMPLETED", "FAILED", name="evaluationstatus"),
                nullable=False,
            ),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("started_at", sa.DateTime(), nullable=True),
            sa.Column("completed_at", sa.DateTime(), nullable=True),
            sa.Column("error_message", sa.String(), nullable=True),
            sa.ForeignKeyConstraint(["portfolio_id"], ["portfolios.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("evaluation_id"),
        )


def downgrade() -> None:
    """Retain the legacy Phase 1 schema, which may predate Alembic tracking."""
    # These tables may have existed before this migration chain. Deliberately do
    # not drop them when reversing later Veyra migrations.
    pass
