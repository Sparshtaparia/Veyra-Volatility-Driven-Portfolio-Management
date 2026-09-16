"""Add Phase 4 intelligence and controlled-signal state.

Revision ID: 0002_phase4_intelligence
Revises: 0001_phase3_volatility_regime
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0002_phase4_intelligence"
down_revision: str | Sequence[str] | None = "0001_phase3_volatility_regime"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _identity_columns(*, portfolio: bool = False) -> list[sa.Column]:
    columns: list[sa.Column] = [
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("evaluation_id", postgresql.UUID(as_uuid=True), nullable=False),
    ]
    if portfolio:
        columns.append(sa.Column("portfolio_id", sa.String(), nullable=False))
    return columns


def _foreign_keys(*, portfolio: bool = False) -> list[sa.ForeignKeyConstraint]:
    constraints = [
        sa.ForeignKeyConstraint(
            ["evaluation_id"], ["evaluations.evaluation_id"], ondelete="CASCADE"
        )
    ]
    if portfolio:
        constraints.append(
            sa.ForeignKeyConstraint(["portfolio_id"], ["portfolios.id"], ondelete="CASCADE")
        )
    return constraints


def upgrade() -> None:
    op.create_table(
        "factor_states",
        *_identity_columns(portfolio=True),
        sa.Column("ticker", sa.String(), nullable=False),
        sa.Column("as_of_date", sa.Date(), nullable=False),
        sa.Column("normalization_method", sa.String(32), nullable=False),
        sa.Column("raw_factors", sa.JSON(), nullable=False),
        sa.Column("normalized_factors", sa.JSON(), nullable=False),
        sa.Column("factor_contributions", sa.JSON(), nullable=False),
        sa.Column("base_signal", sa.Float(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        *_foreign_keys(portfolio=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("evaluation_id", "ticker", name="uq_factor_state_evaluation_ticker"),
    )
    op.create_index("ix_factor_states_evaluation_id", "factor_states", ["evaluation_id"])
    op.create_index(
        "ix_factor_states_portfolio_date", "factor_states", ["portfolio_id", "as_of_date"]
    )

    op.create_table(
        "fama_french_exposures",
        *_identity_columns(),
        sa.Column("ticker", sa.String(), nullable=False),
        sa.Column("as_of_date", sa.Date(), nullable=False),
        sa.Column("alpha", sa.Float(), nullable=False),
        sa.Column("market_beta", sa.Float(), nullable=False),
        sa.Column("smb_beta", sa.Float(), nullable=False),
        sa.Column("hml_beta", sa.Float(), nullable=False),
        sa.Column("rmw_beta", sa.Float(), nullable=False),
        sa.Column("cma_beta", sa.Float(), nullable=False),
        sa.Column("r_squared", sa.Float(), nullable=False),
        sa.Column("observation_count", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        *_foreign_keys(),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("evaluation_id", "ticker", name="uq_ff_exposure_evaluation_ticker"),
    )
    op.create_index("ix_ff_exposures_evaluation_id", "fama_french_exposures", ["evaluation_id"])

    op.create_table(
        "reliability_states",
        *_identity_columns(),
        sa.Column("ticker", sa.String(), nullable=False),
        sa.Column("as_of_date", sa.Date(), nullable=False),
        sa.Column("base_reliability", sa.Float(), nullable=False),
        sa.Column("volatility_adjustment", sa.Float(), nullable=False),
        sa.Column("regime_adjustment", sa.Float(), nullable=False),
        sa.Column("recent_performance_adjustment", sa.Float(), nullable=False),
        sa.Column("reliability_adjustment", sa.Float(), nullable=False),
        sa.Column("effective_reliability", sa.Float(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        *_foreign_keys(),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("evaluation_id", "ticker", name="uq_reliability_evaluation_ticker"),
    )
    op.create_index("ix_reliability_states_evaluation_id", "reliability_states", ["evaluation_id"])

    op.create_table(
        "risk_states",
        *_identity_columns(portfolio=True),
        sa.Column("as_of_date", sa.Date(), nullable=False),
        sa.Column("volatility_risk", sa.Float(), nullable=False),
        sa.Column("drawdown_risk", sa.Float(), nullable=False),
        sa.Column("correlation_risk", sa.Float(), nullable=False),
        sa.Column("concentration_risk", sa.Float(), nullable=False),
        sa.Column("liquidity_risk", sa.Float(), nullable=False),
        sa.Column("composite_risk", sa.Float(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        *_foreign_keys(portfolio=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("evaluation_id", name="uq_risk_state_evaluation"),
    )
    op.create_index("ix_risk_states_portfolio_date", "risk_states", ["portfolio_id", "as_of_date"])

    op.create_table(
        "controlled_signals",
        *_identity_columns(),
        sa.Column("ticker", sa.String(), nullable=False),
        sa.Column("as_of_date", sa.Date(), nullable=False),
        sa.Column("base_signal", sa.Float(), nullable=False),
        sa.Column("volatility_adjustment", sa.Float(), nullable=False),
        sa.Column("reliability_adjustment", sa.Float(), nullable=False),
        sa.Column("risk_adjustment", sa.Float(), nullable=False),
        sa.Column("controlled_signal", sa.Float(), nullable=False),
        sa.Column("risk_contribution", sa.Float(), nullable=False),
        sa.Column("explainability", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        *_foreign_keys(),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "evaluation_id", "ticker", name="uq_controlled_signal_evaluation_ticker"
        ),
    )
    op.create_index("ix_controlled_signals_evaluation_id", "controlled_signals", ["evaluation_id"])


def downgrade() -> None:
    op.drop_table("controlled_signals")
    op.drop_table("risk_states")
    op.drop_table("reliability_states")
    op.drop_table("fama_french_exposures")
    op.drop_table("factor_states")
