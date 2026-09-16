"""
Phase 9: Pipeline Backtest Engine Tests
"""
from datetime import date
import pandas as pd
import pytest

from quant_engine.backtest.models import PipelineBacktestConfig
from quant_engine.backtest.pipeline_engine import PipelineBacktester
from quant_engine.data.models import MarketBar
from quant_engine.data.provider import MockProvider


@pytest.fixture
def mock_data():
    dates = pd.date_range(start="2020-01-01", end="2022-01-01", freq="B").date
    bars = []
    
    for t in ["AAPL", "MSFT", "GOOG"]:
        price = 100.0
        for d in dates:
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
            price *= 1.0001  # Upward drift
    return MockProvider(bars)


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
