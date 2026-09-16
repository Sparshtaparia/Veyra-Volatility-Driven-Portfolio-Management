"""Alembic verification for the non-destructive Phase 3D migration."""

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect

from config.settings import get_settings
from database.models import EvaluationModel, HoldingModel, PortfolioModel


def test_phase3_migration_upgrades_and_downgrades_existing_schema(
    tmp_path,
    monkeypatch,
) -> None:
    database_path = tmp_path / "phase3_migration.sqlite"
    database_url = f"sqlite:///{database_path}"
    engine = create_engine(database_url)
    PortfolioModel.__table__.create(engine)
    HoldingModel.__table__.create(engine)
    EvaluationModel.__table__.create(engine)

    monkeypatch.setenv("DATABASE_URL", database_url)
    get_settings.cache_clear()
    config = Config("alembic.ini")

    command.upgrade(config, "head")

    inspector = inspect(engine)
    assert {
        "volatility_states",
        "regime_states",
        "factor_states",
        "fama_french_exposures",
        "reliability_states",
        "risk_states",
        "controlled_signals",
        "portfolio_targets",
        "rebalance_events",
        "trades",
        "portfolio_snapshots",
        "feedback_updates",
        "backtests",
        "backtest_returns",
        "backtest_metrics",
        "scheduled_runs",
    }.issubset(inspector.get_table_names())
    assert command.current(config) is None

    command.downgrade(config, "base")

    remaining = set(inspect(engine).get_table_names())
    assert "volatility_states" not in remaining
    assert "regime_states" not in remaining
    assert "controlled_signals" not in remaining
    assert "portfolio_targets" not in remaining
    assert "backtests" not in remaining
    assert "scheduled_runs" not in remaining
    assert {"portfolios", "holdings", "evaluations"}.issubset(remaining)
    get_settings.cache_clear()
