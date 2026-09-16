"""Add the Phase 6 scheduled-run operational ledger.

Revision ID: 0004_phase6_operations
Revises: 0003_phase5_portfolio_control
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0004_phase6_operations"
down_revision: str | Sequence[str] | None = "0003_phase5_portfolio_control"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "scheduled_runs",
        sa.Column("run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("run_type", sa.String(32), nullable=False),
        sa.Column("portfolio_id", sa.String(), nullable=False),
        sa.Column("evaluation_date", sa.Date(), nullable=False),
        sa.Column("evaluation_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("provider", sa.String(128), nullable=False),
        sa.Column("started_at", sa.DateTime(), nullable=False),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("duration_ms", sa.Float(), nullable=True),
        sa.Column("stage_timings", sa.JSON(), nullable=False),
        sa.Column("error_type", sa.String(128), nullable=True),
        sa.Column("error_message", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint(
            "run_type IN ('FULL_EVALUATION', 'VOLATILITY_REFRESH')",
            name="ck_scheduled_run_type",
        ),
        sa.CheckConstraint(
            "status IN ('RUNNING', 'COMPLETED', 'FAILED')",
            name="ck_scheduled_run_status",
        ),
        sa.CheckConstraint(
            "duration_ms IS NULL OR duration_ms >= 0",
            name="ck_scheduled_run_duration",
        ),
        sa.ForeignKeyConstraint(
            ["evaluation_id"],
            ["evaluations.evaluation_id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(["portfolio_id"], ["portfolios.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("run_id"),
        sa.UniqueConstraint(
            "run_type",
            "portfolio_id",
            "evaluation_date",
            name="uq_scheduled_run_type_portfolio_date",
        ),
    )
    op.create_index("ix_scheduled_runs_status", "scheduled_runs", ["status"])
    op.create_index(
        "ix_scheduled_runs_portfolio_date",
        "scheduled_runs",
        ["portfolio_id", "evaluation_date"],
    )


def downgrade() -> None:
    op.drop_index("ix_scheduled_runs_portfolio_date", table_name="scheduled_runs")
    op.drop_index("ix_scheduled_runs_status", table_name="scheduled_runs")
    op.drop_table("scheduled_runs")
