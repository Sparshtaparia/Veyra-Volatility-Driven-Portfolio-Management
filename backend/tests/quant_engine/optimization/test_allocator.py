import pytest

from quant_engine.optimization.allocator import TargetAllocator
from quant_engine.optimization.models import AssetOptimizationInput, OptimizationOutput


def test_allocator_calculates_deltas_correctly():
    allocator = TargetAllocator(rebalance_threshold=0.05)
    
    current = [
        AssetOptimizationInput(ticker="AAPL", current_weight=0.6, expected_signal=0, volatility=0, composite_risk_score=0, reliability_score=0),
        AssetOptimizationInput(ticker="MSFT", current_weight=0.4, expected_signal=0, volatility=0, composite_risk_score=0, reliability_score=0),
    ]
    
    targets = [
        OptimizationOutput(ticker="AAPL", target_weight=0.5),
        OptimizationOutput(ticker="MSFT", target_weight=0.5),
    ]
    
    result = allocator.allocate(current, targets)
    
    assert len(result.allocations) == 2
    
    aapl = next(x for x in result.allocations if x.ticker == "AAPL")
    msft = next(x for x in result.allocations if x.ticker == "MSFT")
    
    assert aapl.delta_weight == pytest.approx(-0.1)
    assert msft.delta_weight == pytest.approx(0.1)
    
    # Turnover = sum(|delta|) / 2 = (0.1 + 0.1) / 2 = 0.1
    assert result.total_turnover == pytest.approx(0.1)

def test_allocator_decision_threshold():
    # Turnover = 0.04
    allocator_hold = TargetAllocator(rebalance_threshold=0.05)
    targets_hold = [
        OptimizationOutput(ticker="AAPL", target_weight=0.56),
        OptimizationOutput(ticker="MSFT", target_weight=0.44),
    ]
    
    current = [
        AssetOptimizationInput(ticker="AAPL", current_weight=0.6, expected_signal=0, volatility=0, composite_risk_score=0, reliability_score=0),
        AssetOptimizationInput(ticker="MSFT", current_weight=0.4, expected_signal=0, volatility=0, composite_risk_score=0, reliability_score=0),
    ]
    
    result_hold = allocator_hold.allocate(current, targets_hold)
    assert result_hold.total_turnover == pytest.approx(0.04)
    assert result_hold.decision == "HOLD"
    
    # Turnover = 0.1 (above threshold)
    allocator_rebalance = TargetAllocator(rebalance_threshold=0.05)
    targets_rebalance = [
        OptimizationOutput(ticker="AAPL", target_weight=0.5),
        OptimizationOutput(ticker="MSFT", target_weight=0.5),
    ]
    
    result_rebalance = allocator_rebalance.allocate(current, targets_rebalance)
    assert result_rebalance.total_turnover == pytest.approx(0.1)
    assert result_rebalance.decision == "REBALANCE_REQUIRED"
