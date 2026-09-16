"""Add Phase 3 volatility and regime state tables.

Revision ID: 0001_phase3_volatility_regime
Revises: 0000_phase1_baseline
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001_phase3_volatility_regime"
down_revision: str | Sequence[str] | None = "0000_phase1_baseline"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "volatility_states",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("evaluation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("portfolio_id", sa.String(), nullable=False),
        sa.Column("ticker", sa.String(), nullable=False),
        sa.Column("as_of_date", sa.Date(), nullable=False),
        sa.Column("omega", sa.Float(), nullable=True),
        sa.Column("alpha", sa.Float(), nullable=True),
        sa.Column("gamma", sa.Float(), nullable=True),
        sa.Column("beta", sa.Float(), nullable=True),
        sa.Column("persistence", sa.Float(), nullable=True),
        sa.Column("conditional_variance", sa.Float(), nullable=False),
        sa.Column("conditional_volatility", sa.Float(), nullable=False),
        sa.Column("forecast_volatility", sa.Float(), nullable=False),
        sa.Column("realized_volatility", sa.Float(), nullable=False),
        sa.Column("volatility_ratio", sa.Float(), nullable=False),
        sa.Column("fit_status", sa.String(length=32), nullable=False),
        sa.Column("convergence_status", sa.String(length=32), nullable=False),
        sa.Column("observation_count", sa.Integer(), nullable=False),
        sa.Column("used_fallback", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint("conditional_variance >= 0", name="ck_vol_state_variance"),
        sa.CheckConstraint("conditional_volatility >= 0", name="ck_vol_state_conditional"),
        sa.CheckConstraint("forecast_volatility >= 0", name="ck_vol_state_forecast"),
        sa.CheckConstraint("realized_volatility >= 0", name="ck_vol_state_realized"),
        sa.CheckConstraint("volatility_ratio >= 0", name="ck_vol_state_ratio"),
        sa.CheckConstraint("observation_count >= 0", name="ck_vol_state_observations"),
        sa.ForeignKeyConstraint(
            ["evaluation_id"], ["evaluations.evaluation_id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["portfolio_id"], ["portfolios.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "evaluation_id",
            "ticker",
            "as_of_date",
            name="uq_volatility_state_evaluation_ticker_date",
        ),
    )
    op.create_index(
        "ix_volatility_states_evaluation_id",
        "volatility_states",
        ["evaluation_id"],
    )
    op.create_index(
        "ix_volatility_states_portfolio_date",
        "volatility_states",
        ["portfolio_id", "as_of_date"],
    )
    op.create_index(
        "ix_volatility_states_ticker_date",
        "volatility_states",
        ["ticker", "as_of_date"],
    )

    op.create_table(
        "regime_states",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("evaluation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("portfolio_id", sa.String(), nullable=False),
        sa.Column("as_of_date", sa.Date(), nullable=False),
        sa.Column("total_asset_count", sa.Integer(), nullable=False),
        sa.Column("eligible_asset_count", sa.Integer(), nullable=False),
        sa.Column("model_fit_count", sa.Integer(), nullable=False),
        sa.Column("fallback_count", sa.Integer(), nullable=False),
        sa.Column("failed_asset_count", sa.Integer(), nullable=False),
        sa.Column("excluded_count", sa.Integer(), nullable=False),
        sa.Column("aggregate_volatility", sa.Float(), nullable=False),
        sa.Column("median_realized_volatility", sa.Float(), nullable=False),
        sa.Column("median_volatility_ratio", sa.Float(), nullable=False),
        sa.Column("ratio_iqr", sa.Float(), nullable=False),
        sa.Column("stress_score", sa.Float(), nullable=False),
        sa.Column("adaptive_threshold", sa.Float(), nullable=False),
        sa.Column("distance_to_threshold", sa.Float(), nullable=False),
        sa.Column("regime", sa.String(length=32), nullable=False),
        sa.Column("coverage_ratio", sa.Float(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint("total_asset_count > 0", name="ck_regime_total_assets"),
        sa.CheckConstraint("eligible_asset_count >= 0", name="ck_regime_eligible_assets"),
        sa.CheckConstraint("model_fit_count >= 0", name="ck_regime_fit_count"),
        sa.CheckConstraint("fallback_count >= 0", name="ck_regime_fallback_count"),
        sa.CheckConstraint("failed_asset_count >= 0", name="ck_regime_failed_count"),
        sa.CheckConstraint("excluded_count >= 0", name="ck_regime_excluded_count"),
        sa.CheckConstraint("aggregate_volatility >= 0", name="ck_regime_aggregate_vol"),
        sa.CheckConstraint("median_realized_volatility >= 0", name="ck_regime_realized_vol"),
        sa.CheckConstraint("median_volatility_ratio >= 0", name="ck_regime_median_ratio"),
        sa.CheckConstraint("ratio_iqr >= 0", name="ck_regime_ratio_iqr"),
        sa.CheckConstraint("stress_score >= 0", name="ck_regime_stress_score"),
        sa.CheckConstraint("adaptive_threshold >= 0", name="ck_regime_threshold"),
        sa.CheckConstraint(
            "coverage_ratio >= 0 AND coverage_ratio <= 1",
            name="ck_regime_coverage_ratio",
        ),
        sa.ForeignKeyConstraint(
            ["evaluation_id"], ["evaluations.evaluation_id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["portfolio_id"], ["portfolios.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("evaluation_id", "as_of_date", name="uq_regime_state_evaluation_date"),
    )
    op.create_index("ix_regime_states_evaluation_id", "regime_states", ["evaluation_id"])
    op.create_index(
        "ix_regime_states_portfolio_date",
        "regime_states",
        ["portfolio_id", "as_of_date"],
    )


def downgrade() -> None:
    op.drop_index("ix_regime_states_portfolio_date", table_name="regime_states")
    op.drop_index("ix_regime_states_evaluation_id", table_name="regime_states")
    op.drop_table("regime_states")
    op.drop_index("ix_volatility_states_ticker_date", table_name="volatility_states")
    op.drop_index("ix_volatility_states_portfolio_date", table_name="volatility_states")
    op.drop_index("ix_volatility_states_evaluation_id", table_name="volatility_states")
    op.drop_table("volatility_states")
