from typing import Dict, Sequence
from uuid import UUID

from quant_engine.optimization.models import AllocationResult
from quant_engine.rebalance.models import RebalanceAction, RebalanceOrder, RebalancePlan

class RebalancePlanner:
    """
    Phase 7 Rebalance Planner.
    Converts target weights into actionable trade plans based on absolute dollar values.
    """

    def __init__(self, significance_threshold_value: float = 1.0):
        """
        :param significance_threshold_value: Minimum dollar value for a trade to be considered significant.
        """
        self.significance_threshold_value = significance_threshold_value

    def generate_plan(
        self,
        evaluation_id: UUID,
        portfolio_id: str,
        allocation: AllocationResult,
        current_prices: Dict[str, float],
        portfolio_value: float
    ) -> RebalancePlan:
        
        if allocation.decision == "HOLD":
            return RebalancePlan(
                evaluation_id=evaluation_id,
                portfolio_id=portfolio_id,
                orders=[],
                total_turnover=allocation.total_turnover,
                valid=True,
                decision="HOLD"
            )

        orders = []
        for alloc in allocation.allocations:
            ticker = alloc.ticker
            if ticker not in current_prices:
                raise ValueError(f"Missing current price for {ticker}")
                
            price = current_prices[ticker]
            if price <= 0.0:
                raise ValueError(f"Invalid price for {ticker}: {price}")

            current_val = alloc.current_weight * portfolio_value
            target_val = alloc.target_weight * portfolio_value
            delta_val = target_val - current_val
            
            # Filter insignificant trades
            if abs(delta_val) < self.significance_threshold_value:
                action = RebalanceAction.HOLD
                qty = 0.0
            else:
                action = RebalanceAction.BUY if delta_val > 0 else RebalanceAction.SELL
                qty = abs(delta_val) / price

            order = RebalanceOrder(
                ticker=ticker,
                action=action,
                current_weight=alloc.current_weight,
                target_weight=alloc.target_weight,
                weight_delta=alloc.delta_weight,
                current_value=current_val,
                target_value=target_val,
                delta_value=delta_val,
                current_price=price,
                quantity=qty
            )
            
            # Always add to order list so we have full visibility, but the Executor will only act on BUY/SELL
            orders.append(order)

        return RebalancePlan(
            evaluation_id=evaluation_id,
            portfolio_id=portfolio_id,
            orders=orders,
            total_turnover=allocation.total_turnover,
            valid=True,
            decision="REBALANCE_REQUIRED"
        )
