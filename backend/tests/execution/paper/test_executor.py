import pytest
from uuid import uuid4
from datetime import datetime

from quant_engine.rebalance.models import RebalanceAction, RebalanceOrder, RebalancePlan
from execution.paper.executor import PaperExecutor
from execution.paper.models import OrderStatus

def test_paper_executor_buy_sell():
    executor = PaperExecutor(slippage_bps=10.0, transaction_cost_bps=5.0)
    
    plan = RebalancePlan(
        evaluation_id=uuid4(),
        portfolio_id="port_1",
        total_turnover=0.5,
        valid=True,
        decision="REBALANCE_REQUIRED",
        orders=[
            RebalanceOrder(
                ticker="AAPL",
                action=RebalanceAction.BUY,
                current_weight=0.0,
                target_weight=0.5,
                weight_delta=0.5,
                current_value=0.0,
                target_value=5000.0,
                delta_value=5000.0,
                current_price=100.0,
                quantity=50.0
            ),
            RebalanceOrder(
                ticker="MSFT",
                action=RebalanceAction.SELL,
                current_weight=0.5,
                target_weight=0.0,
                weight_delta=-0.5,
                current_value=5000.0,
                target_value=0.0,
                delta_value=-5000.0,
                current_price=200.0,
                quantity=25.0
            )
        ]
    )
    
    current_holdings = [
        {"ticker": "MSFT", "quantity": 25.0, "average_price": 180.0, "current_price": 200.0, "market_value": 5000.0, "weight": 0.5}
    ]
    
    result = executor.execute(plan, current_holdings)
    
    assert len(result.orders) == 2
    
    aapl_order = next(o for o in result.orders if o.ticker == "AAPL")
    assert aapl_order.status == OrderStatus.FILLED
    # slippage is 10 bps = 0.001 * 100 = 0.1
    # buy price = 100 + 0.1 = 100.1
    assert aapl_order.execution_price == 100.1
    assert aapl_order.gross_notional == 5005.0
    
    msft_order = next(o for o in result.orders if o.ticker == "MSFT")
    assert msft_order.status == OrderStatus.FILLED
    # slippage is 0.2, sell price = 199.8
    assert msft_order.execution_price == 199.8
    assert msft_order.gross_notional == 4995.0
    
    # Check simulated holdings
    assert len(result.simulated_holdings) == 2
    
    aapl_holding = next(h for h in result.simulated_holdings if h["ticker"] == "AAPL")
    assert aapl_holding["quantity"] == 50.0
    
    msft_holding = next(h for h in result.simulated_holdings if h["ticker"] == "MSFT")
    assert msft_holding["quantity"] == 0.0

from pydantic import ValidationError

def test_paper_executor_rejects_invalid_quantity():
    with pytest.raises(ValidationError):
        RebalanceOrder(
            ticker="AAPL", action=RebalanceAction.BUY, current_weight=0, target_weight=0.5, weight_delta=0.5,
            current_value=0, target_value=100, delta_value=100, current_price=100,
            quantity=-10.0 # INVALID
        )
