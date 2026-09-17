from uuid import uuid4

import pytest

from quant_engine.optimization.models import AllocationDelta, AllocationResult
from quant_engine.rebalance.models import RebalanceAction
from quant_engine.rebalance.service import RebalancePlanner


def test_planner_buy_sell_hold():
    planner = RebalancePlanner(significance_threshold_value=1.0)
    
    allocations = [
        # AAPL: current 0.2, target 0.3 -> BUY
        AllocationDelta(ticker="AAPL", current_weight=0.2, target_weight=0.3, delta_weight=0.1),
        # MSFT: current 0.5, target 0.3 -> SELL
        AllocationDelta(ticker="MSFT", current_weight=0.5, target_weight=0.3, delta_weight=-0.2),
        # GOOGL: current 0.3, target 0.3 -> HOLD (insignificant delta)
        AllocationDelta(ticker="GOOGL", current_weight=0.3, target_weight=0.300001, delta_weight=0.000001)
    ]
    
    alloc_result = AllocationResult(allocations=allocations, total_turnover=0.3, valid=True, decision="REBALANCE_REQUIRED")
    
    current_prices = {
        "AAPL": 150.0,
        "MSFT": 300.0,
        "GOOGL": 2800.0
    }
    
    portfolio_value = 100000.0 # AAPL target=30k(buy 10k=66.66), MSFT target=30k(sell 20k=66.66), GOOGL target=30k(hold)
    
    plan = planner.generate_plan(
        evaluation_id=uuid4(),
        portfolio_id="test_port",
        allocation=alloc_result,
        current_prices=current_prices,
        portfolio_value=portfolio_value
    )
    
    assert plan.decision == "REBALANCE_REQUIRED"
    assert len(plan.orders) == 3
    
    aapl_order = next(o for o in plan.orders if o.ticker == "AAPL")
    assert aapl_order.action == RebalanceAction.BUY
    assert aapl_order.delta_value == 10000.0
    assert aapl_order.quantity == pytest.approx(66.6666, rel=1e-3)
    
    msft_order = next(o for o in plan.orders if o.ticker == "MSFT")
    assert msft_order.action == RebalanceAction.SELL
    assert msft_order.delta_value == -20000.0
    assert msft_order.quantity == pytest.approx(66.6666, rel=1e-3)
    
    googl_order = next(o for o in plan.orders if o.ticker == "GOOGL")
    assert googl_order.action == RebalanceAction.HOLD
    assert googl_order.quantity == 0.0

def test_planner_invalid_price():
    planner = RebalancePlanner()
    alloc_result = AllocationResult(
        allocations=[AllocationDelta(ticker="AAPL", current_weight=0, target_weight=0.5, delta_weight=0.5)],
        total_turnover=0.5, valid=True, decision="REBALANCE_REQUIRED"
    )
    with pytest.raises(ValueError):
        planner.generate_plan(uuid4(), "p1", alloc_result, current_prices={"AAPL": -10}, portfolio_value=100)
