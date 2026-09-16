"""Unit tests for Phase 5 portfolio control, feedback, and backtesting."""

from datetime import date

import numpy as np
import pandas as pd
import pytest

from quant_engine.backtest.ablation import AblationRunner
from quant_engine.backtest.engine import BacktestEngine
from quant_engine.backtest.models import AblationVariant
from quant_engine.feedback.engine import FeedbackController
from quant_engine.feedback.models import FeedbackOutcome, SystemState
from quant_engine.portfolio.exposure import ExposureController
from quant_engine.portfolio.models import (
    AssetAllocationInput,
    ExposureConfig,
    OptimizerConfig,
    TargetWeight,
    TradeSide,
)
from quant_engine.portfolio.optimizer import PortfolioOptimizer
from quant_engine.portfolio.rebalance import RebalanceEngine, SimulatedExecutor
from quant_engine.volatility.models import MarketRegime


def test_exposure_controller_couples_regime_and_risk() -> None:
    controller = ExposureController(ExposureConfig(base_exposure=1.0, risk_sensitivity=0.5))
    normal = controller.calculate(MarketRegime.NORMAL, 0.2)
    stressed = controller.calculate(MarketRegime.HIGH_STRESS, 0.8)

    assert normal.target_gross_exposure == pytest.approx(0.9)
    assert stressed.target_gross_exposure < normal.target_gross_exposure
    assert stressed.target_net_exposure == stressed.target_gross_exposure


def test_optimizer_preserves_inverse_volatility_and_constraints() -> None:
    assets = [
        AssetAllocationInput(
            ticker="LOW",
            sector="A",
            current_weight=0.5,
            controlled_signal=0.1,
            conditional_volatility=0.01,
        ),
        AssetAllocationInput(
            ticker="HIGH",
            sector="B",
            current_weight=0.5,
            controlled_signal=0.1,
            conditional_volatility=0.02,
        ),
    ]
    exposure = ExposureController().calculate(MarketRegime.NORMAL, 0.4)
    result = PortfolioOptimizer(
        OptimizerConfig(
            max_stock_weight=0.6,
            max_sector_exposure=0.6,
            target_volatility=0.30,
            signal_strength=0.0,
            turnover_penalty=0.0,
        )
    ).optimize(date(2026, 1, 1), assets, exposure)

    target = {item.ticker: item for item in result.targets}
    assert target["LOW"].inverse_volatility_weight > target["HIGH"].inverse_volatility_weight
    assert all(item.target_weight <= 0.6 + 1e-7 for item in result.targets)
    assert result.expected_volatility <= 0.30 + 1e-6
    assert result.cash_weight >= 0.0


def test_rebalance_and_paper_execution_include_costs() -> None:
    targets = [
        TargetWeight(
            ticker="A",
            sector="X",
            current_weight=0.4,
            inverse_volatility_weight=0.5,
            target_weight=0.5,
            weight_change=0.1,
        )
    ]
    instructions = RebalanceEngine().calculate(targets, 10_000.0, {"A": 100.0})
    trades = SimulatedExecutor(transaction_cost_bps=5.0, slippage_bps=10.0).execute(instructions)

    assert instructions[0].side is TradeSide.BUY
    assert instructions[0].trade_quantity == pytest.approx(10.0)
    assert trades[0].execution_price > trades[0].reference_price
    assert trades[0].transaction_cost > 0.0
    assert trades[0].slippage_cost > 0.0


def test_feedback_controller_updates_all_state_dimensions() -> None:
    previous = SystemState(
        as_of_date=date(2026, 1, 1),
        volatility_distribution_level=0.02,
        adaptive_threshold=1.2,
        reliability_multiplier=0.8,
        risk_limit=0.7,
        exposure_limit=0.9,
        portfolio_value=100_000.0,
    )
    outcome = FeedbackOutcome(
        observation_date=date(2026, 2, 1),
        portfolio_return=-0.05,
        realized_volatility=0.04,
        drawdown=0.10,
        signal_accuracy=-0.5,
        transaction_cost=100.0,
    )
    update = FeedbackController().update(previous, -0.3, outcome)

    assert (
        update.updated_state.volatility_distribution_level > previous.volatility_distribution_level
    )
    assert update.updated_state.reliability_multiplier < previous.reliability_multiplier
    assert update.updated_state.exposure_limit < previous.exposure_limit
    assert update.updated_state.portfolio_value < previous.portfolio_value


def backtest_inputs():
    dates = pd.date_range("2025-01-01", periods=100, freq="D")
    returns = pd.DataFrame({"A": np.full(100, 0.001), "B": np.full(100, -0.0002)}, index=dates)
    weights = pd.DataFrame(
        {"A": [0.6, 0.7, 0.8], "B": [0.3, 0.2, 0.1]},
        index=[dates[0], dates[31], dates[59]],
    )
    benchmark = pd.Series(np.full(100, 0.0003), index=dates)
    return dates, returns, weights, benchmark


def test_backtest_dates_costs_metrics_and_attribution() -> None:
    _, returns, weights, benchmark = backtest_inputs()
    result = BacktestEngine().run("walk-forward", returns, weights, benchmark)

    assert all(item.signal_date < item.return_realization_date for item in result.returns)
    assert sum(item.transaction_cost for item in result.returns) > 0.0
    assert result.metrics.total_return > 0.0
    assert result.metrics.turnover > 0.0
    assert len(result.attribution) == 2


def test_backtest_does_not_use_future_target_weights() -> None:
    dates = pd.date_range("2025-01-01", periods=40, freq="D")
    returns = pd.DataFrame({"A": np.full(40, 0.01), "B": np.full(40, -0.01)}, index=dates)
    weights = pd.DataFrame(
        {"A": [1.0, 0.0], "B": [0.0, 1.0]},
        index=[dates[0], dates[20]],
    )

    result = BacktestEngine().run("lookahead", returns, weights, pd.Series(0.0, index=dates))
    january = [item for item in result.returns if item.return_realization_date.month == 1]

    assert january
    assert all(item.signal_date == dates[0].date() for item in january)
    assert all(item.gross_return == pytest.approx(0.01) for item in january)


def test_ablation_runs_all_required_variants() -> None:
    _, returns, weights, benchmark = backtest_inputs()
    results = AblationRunner().run(
        returns,
        benchmark,
        {variant: weights for variant in AblationVariant},
    )
    assert set(results) == set(AblationVariant)
    assert all(result.metrics.volatility >= 0.0 for result in results.values())
