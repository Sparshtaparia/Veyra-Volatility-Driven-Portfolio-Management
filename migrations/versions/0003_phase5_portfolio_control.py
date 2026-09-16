"""Add Phase 5 portfolio control, feedback, and backtest state.

Revision ID: 0003_phase5_portfolio_control
Revises: 0002_phase4_intelligence
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0003_phase5_portfolio_control"
down_revision: str | Sequence[str] | None = "0002_phase4_intelligence"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "portfolio_targets",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("evaluation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("portfolio_id", sa.String(), nullable=False),
        sa.Column("as_of_date", sa.Date(), nullable=False),
        sa.Column("ticker", sa.String(), nullable=False),
        sa.Column("sector", sa.String(), nullable=False),
        sa.Column("current_weight", sa.Float(), nullable=False),
        sa.Column("inverse_volatility_weight", sa.Float(), nullable=False),
        sa.Column("target_weight", sa.Float(), nullable=False),
        sa.Column("weight_change", sa.Float(), nullable=False),
        sa.Column("gross_exposure", sa.Float(), nullable=False),
        sa.Column("net_exposure", sa.Float(), nullable=False),
        sa.Column("cash_weight", sa.Float(), nullable=False),
        sa.Column("expected_volatility", sa.Float(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["evaluation_id"], ["evaluations.evaluation_id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["portfolio_id"], ["portfolios.id"], ondelete="CASCADE"),
        sa.UniqueConstraint(
            "evaluation_id", "ticker", name="uq_portfolio_target_evaluation_ticker"
        ),
        sa.CheckConstraint("current_weight >= 0 AND current_weight <= 1", name="ck_target_current"),
        sa.CheckConstraint("target_weight >= 0 AND target_weight <= 1", name="ck_target_weight"),
        sa.CheckConstraint("gross_exposure >= 0 AND gross_exposure <= 1", name="ck_target_gross"),
        sa.CheckConstraint("net_exposure >= 0 AND net_exposure <= 1", name="ck_target_net"),
        sa.CheckConstraint("cash_weight >= 0 AND cash_weight <= 1", name="ck_target_cash"),
        sa.CheckConstraint("expected_volatility >= 0", name="ck_target_volatility"),
    )
    op.create_index(
        "ix_portfolio_targets_portfolio_date", "portfolio_targets", ["portfolio_id", "as_of_date"]
    )

    op.create_table(
        "rebalance_events",
        sa.Column("event_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("evaluation_id", postgresql.UUID(as_uuid=True), nullable=False, unique=True),
        sa.Column("portfolio_id", sa.String(), nullable=False),
        sa.Column("event_date", sa.Date(), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("portfolio_value", sa.Float(), nullable=False),
        sa.Column("turnover", sa.Float(), nullable=False),
        sa.Column("total_cost", sa.Float(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["evaluation_id"], ["evaluations.evaluation_id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["portfolio_id"], ["portfolios.id"], ondelete="CASCADE"),
        sa.CheckConstraint("portfolio_value >= 0", name="ck_rebalance_value"),
        sa.CheckConstraint("turnover >= 0", name="ck_rebalance_turnover"),
        sa.CheckConstraint("total_cost >= 0", name="ck_rebalance_cost"),
    )
    op.create_table(
        "trades",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("event_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("ticker", sa.String(), nullable=False),
        sa.Column("side", sa.String(8), nullable=False),
        sa.Column("quantity", sa.Float(), nullable=False),
        sa.Column("reference_price", sa.Float(), nullable=False),
        sa.Column("execution_price", sa.Float(), nullable=False),
        sa.Column("gross_notional", sa.Float(), nullable=False),
        sa.Column("transaction_cost", sa.Float(), nullable=False),
        sa.Column("slippage_cost", sa.Float(), nullable=False),
        sa.Column("net_cash_change", sa.Float(), nullable=False),
        sa.Column("executed_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["event_id"], ["rebalance_events.event_id"], ondelete="CASCADE"),
        sa.CheckConstraint("side IN ('BUY', 'SELL')", name="ck_trade_side"),
        sa.CheckConstraint("quantity > 0", name="ck_trade_quantity"),
        sa.CheckConstraint("reference_price > 0", name="ck_trade_reference_price"),
        sa.CheckConstraint("execution_price > 0", name="ck_trade_execution_price"),
        sa.CheckConstraint("gross_notional > 0", name="ck_trade_notional"),
        sa.CheckConstraint("transaction_cost >= 0", name="ck_trade_transaction_cost"),
        sa.CheckConstraint("slippage_cost >= 0", name="ck_trade_slippage_cost"),
    )
    op.create_index("ix_trades_event_id", "trades", ["event_id"])

    op.create_table(
        "portfolio_snapshots",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("portfolio_id", sa.String(), nullable=False),
        sa.Column("evaluation_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("snapshot_date", sa.Date(), nullable=False),
        sa.Column("portfolio_value", sa.Float(), nullable=False),
        sa.Column("cash_value", sa.Float(), nullable=False),
        sa.Column("gross_exposure", sa.Float(), nullable=False),
        sa.Column("net_exposure", sa.Float(), nullable=False),
        sa.Column("holdings", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["portfolio_id"], ["portfolios.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["evaluation_id"], ["evaluations.evaluation_id"], ondelete="SET NULL"
        ),
        sa.UniqueConstraint("portfolio_id", "snapshot_date", name="uq_portfolio_snapshot_date"),
        sa.CheckConstraint("portfolio_value >= 0", name="ck_snapshot_value"),
        sa.CheckConstraint("cash_value >= 0", name="ck_snapshot_cash"),
        sa.CheckConstraint("gross_exposure >= 0 AND gross_exposure <= 1", name="ck_snapshot_gross"),
        sa.CheckConstraint("net_exposure >= 0 AND net_exposure <= 1", name="ck_snapshot_net"),
    )
    op.create_index(
        "ix_portfolio_snapshots_portfolio_date",
        "portfolio_snapshots",
        ["portfolio_id", "snapshot_date"],
    )

    op.create_table(
        "feedback_updates",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("evaluation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("portfolio_id", sa.String(), nullable=False),
        sa.Column("observation_date", sa.Date(), nullable=False),
        sa.Column("previous_state", sa.JSON(), nullable=False),
        sa.Column("controlled_signal", sa.Float(), nullable=False),
        sa.Column("observed_outcome", sa.JSON(), nullable=False),
        sa.Column("updated_state", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["evaluation_id"], ["evaluations.evaluation_id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["portfolio_id"], ["portfolios.id"], ondelete="CASCADE"),
    )
    op.create_index(
        "ix_feedback_updates_portfolio_date",
        "feedback_updates",
        ["portfolio_id", "observation_date"],
    )

    op.create_table(
        "backtests",
        sa.Column("backtest_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("portfolio_id", sa.String(), nullable=True),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("variant", sa.String(64), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("configuration", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["portfolio_id"], ["portfolios.id"], ondelete="SET NULL"),
    )
    op.create_table(
        "backtest_returns",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("backtest_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("signal_date", sa.Date(), nullable=False),
        sa.Column("rebalance_date", sa.Date(), nullable=False),
        sa.Column("execution_date", sa.Date(), nullable=False),
        sa.Column("return_realization_date", sa.Date(), nullable=False),
        sa.Column("gross_return", sa.Float(), nullable=False),
        sa.Column("net_return", sa.Float(), nullable=False),
        sa.Column("benchmark_return", sa.Float(), nullable=False),
        sa.Column("turnover", sa.Float(), nullable=False),
        sa.Column("transaction_cost", sa.Float(), nullable=False),
        sa.ForeignKeyConstraint(["backtest_id"], ["backtests.backtest_id"], ondelete="CASCADE"),
        sa.UniqueConstraint(
            "backtest_id", "return_realization_date", name="uq_backtest_return_date"
        ),
        sa.CheckConstraint("turnover >= 0", name="ck_backtest_return_turnover"),
        sa.CheckConstraint("transaction_cost >= 0", name="ck_backtest_return_cost"),
    )
    op.create_index(
        "ix_backtest_returns_backtest_date",
        "backtest_returns",
        ["backtest_id", "return_realization_date"],
    )
    op.create_table(
        "backtest_metrics",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("backtest_id", postgresql.UUID(as_uuid=True), nullable=False, unique=True),
        sa.Column("total_return", sa.Float(), nullable=False),
        sa.Column("cagr", sa.Float(), nullable=False),
        sa.Column("sharpe", sa.Float(), nullable=False),
        sa.Column("sortino", sa.Float(), nullable=False),
        sa.Column("calmar", sa.Float(), nullable=False),
        sa.Column("max_drawdown", sa.Float(), nullable=False),
        sa.Column("volatility", sa.Float(), nullable=False),
        sa.Column("win_rate", sa.Float(), nullable=False),
        sa.Column("turnover", sa.Float(), nullable=False),
        sa.Column("alpha", sa.Float(), nullable=False),
        sa.Column("beta", sa.Float(), nullable=False),
        sa.Column("attribution", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["backtest_id"], ["backtests.backtest_id"], ondelete="CASCADE"),
        sa.CheckConstraint("max_drawdown >= 0", name="ck_backtest_metric_drawdown"),
        sa.CheckConstraint("volatility >= 0", name="ck_backtest_metric_volatility"),
        sa.CheckConstraint("win_rate >= 0 AND win_rate <= 1", name="ck_backtest_metric_win_rate"),
        sa.CheckConstraint("turnover >= 0", name="ck_backtest_metric_turnover"),
    )


def downgrade() -> None:
    op.drop_table("backtest_metrics")
    op.drop_index("ix_backtest_returns_backtest_date", table_name="backtest_returns")
    op.drop_table("backtest_returns")
    op.drop_table("backtests")
    op.drop_index("ix_feedback_updates_portfolio_date", table_name="feedback_updates")
    op.drop_table("feedback_updates")
    op.drop_index("ix_portfolio_snapshots_portfolio_date", table_name="portfolio_snapshots")
    op.drop_table("portfolio_snapshots")
    op.drop_index("ix_trades_event_id", table_name="trades")
    op.drop_table("trades")
    op.drop_table("rebalance_events")
    op.drop_index("ix_portfolio_targets_portfolio_date", table_name="portfolio_targets")
    op.drop_table("portfolio_targets")
