"""
Phase 9: Pipeline Backtest Engine Tests
"""
from datetime import date
from math import sin

import pandas as pd
import pytest

import backend.services.volatility_evaluation_service as volatility_service_module
from quant_engine.backtest.models import PipelineBacktestConfig
from quant_engine.backtest.pipeline_engine import PipelineBacktester
from quant_engine.data.models import MarketBar
from quant_engine.data.provider import MockProvider
from quant_engine.regimes.service import RegimeService
from quant_engine.regimes.threshold import RollingQuantileThreshold


class BacktestMockProvider(MockProvider):
    """Mock history provider with the latest-price helper used by paper execution."""

    def get_latest_price(self, ticker, as_of_date):
        bars = self.get_history(ticker, date(1900, 1, 1), as_of_date)
        if not bars:
            raise ValueError(f"No price available for {ticker}")
        return bars[-1].close


@pytest.fixture
def mock_data(monkeypatch):
    # A new in-memory integration run has no persisted stress history. Use the
    # same rolling-quantile strategy with a deterministic one-point bootstrap;
    # production retains its normal 21-observation requirement.
    monkeypatch.setattr(
        volatility_service_module,
        "RegimeService",
        lambda: RegimeService(
            threshold_strategy=RollingQuantileThreshold(minimum_history=1)
        ),
    )
    dates = pd.date_range(start="2020-01-01", end="2022-01-01", freq="B").date
    bars = []
    
    assets = [("CASH", 1.0), ("AAPL", 100.0), ("MSFT", 100.0), ("GOOG", 100.0)]
    for asset_index, (t, starting_price) in enumerate(assets):
        price = starting_price
        for day_index, d in enumerate(dates):
            bars.append(
                MarketBar(
                    ticker=t,
                    timestamp=d,
                    open=price,
                    high=price * 1.01,
                    low=price * 0.99,
                    close=price,
                    volume=1000,
                )
            )
            # Reproducible drift with small cyclical variation. This avoids
            # zero-variance returns while remaining deterministic.
            daily_return = 0.0003 + 0.0015 * sin((day_index + 3 * asset_index) / 13.0)
            price *= 1.0 + daily_return
    return BacktestMockProvider(bars)


def test_pipeline_backtest_initialization(mock_data):
    config = PipelineBacktestConfig(
        start_date=date(2021, 1, 1),
        end_date=date(2021, 12, 31),
        universe=["AAPL", "MSFT", "GOOG"],
    )
    engine = PipelineBacktester(mock_data, config)
    assert engine.config == config


def test_pipeline_backtest_execution(mock_data):
    config = PipelineBacktestConfig(
        start_date=date(2021, 1, 1),
        end_date=date(2021, 12, 31),
        universe=["AAPL", "MSFT", "GOOG"],
        rebalance_threshold=0.01,
    )
    engine = PipelineBacktester(mock_data, config)
    
    # Generate mock benchmark (flat returns)
    eval_dates = pd.date_range(start=config.start_date, end=config.end_date, freq="BME").date
    bench = pd.Series([0.0]*len(eval_dates), index=eval_dates)
    
    result = engine.run("Test Pipeline", bench)
    
    assert result.evaluations_count == len(eval_dates)
    assert result.config == config
    assert result.name == "Test Pipeline"
    
    # Verify no lookahead: the result records must be chronological
    prev_date = date(1900, 1, 1)
    for record in result.records:
        assert record.evaluation_date > prev_date
        prev_date = record.evaluation_date
        
    # Verify transaction costs are applied if rebalanced
    if result.rebalances_count > 0:
        assert sum(r.transaction_cost for r in result.records) > 0.0

    # Test metric calculations
    assert result.metrics.total_return != 0
    assert result.metrics.volatility >= 0
