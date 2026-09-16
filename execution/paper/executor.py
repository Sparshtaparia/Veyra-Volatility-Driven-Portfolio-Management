from datetime import datetime
from typing import List

from quant_engine.rebalance.models import RebalanceAction, RebalancePlan
from execution.paper.models import OrderStatus, PaperExecutionResult, PaperOrder

class PaperExecutor:
    """
    Simulates execution of a RebalancePlan.
    """

    def __init__(self, slippage_bps: float = 0.0, transaction_cost_bps: float = 0.0):
        self.slippage_bps = slippage_bps
        self.transaction_cost_bps = transaction_cost_bps

    def execute(self, plan: RebalancePlan, current_holdings: List[dict]) -> PaperExecutionResult:
        orders = []
        total_cost = 0.0
        
        # We need a mutable dictionary for holding simulation
        sim_holdings = {h["ticker"]: h for h in current_holdings}

        for p_order in plan.orders:
            if p_order.action == RebalanceAction.HOLD:
                continue

            try:
                # Validation
                if p_order.quantity <= 0:
                    raise ValueError("Quantity must be positive")
                if p_order.current_price <= 0:
                    raise ValueError("Price must be positive")

                # Execution details
                slippage = p_order.current_price * (self.slippage_bps / 10000.0)
                execution_price = p_order.current_price + slippage if p_order.action == RebalanceAction.BUY else p_order.current_price - slippage
                
                gross_notional = execution_price * p_order.quantity
                transaction_cost = gross_notional * (self.transaction_cost_bps / 10000.0)
                
                net_cash_change = -gross_notional - transaction_cost if p_order.action == RebalanceAction.BUY else gross_notional - transaction_cost
                
                total_cost += transaction_cost + (p_order.quantity * slippage)

                order = PaperOrder(
                    ticker=p_order.ticker,
                    side=p_order.action.value,
                    quantity=p_order.quantity,
                    reference_price=p_order.current_price,
                    execution_price=execution_price,
                    gross_notional=gross_notional,
                    transaction_cost=transaction_cost,
                    slippage_cost=p_order.quantity * slippage,
                    net_cash_change=net_cash_change,
                    status=OrderStatus.FILLED,
                    executed_at=datetime.utcnow()
                )
                
                # Apply simulated trade to holdings
                if p_order.ticker not in sim_holdings:
                    sim_holdings[p_order.ticker] = {
                        "ticker": p_order.ticker,
                        "quantity": 0.0,
                        "average_price": execution_price,
                        "current_price": execution_price,
                        "market_value": 0.0,
                        "weight": 0.0
                    }
                
                h = sim_holdings[p_order.ticker]
                if p_order.action == RebalanceAction.BUY:
                    new_qty = h["quantity"] + p_order.quantity
                    # Update average price
                    total_spent = (h["quantity"] * h["average_price"]) + gross_notional
                    h["average_price"] = total_spent / new_qty if new_qty > 0 else 0
                    h["quantity"] = new_qty
                else: # SELL
                    h["quantity"] = max(0.0, h["quantity"] - p_order.quantity)
                    
                h["current_price"] = execution_price
                h["market_value"] = h["quantity"] * h["current_price"]
                
                orders.append(order)
                
            except Exception as e:
                orders.append(PaperOrder(
                    ticker=p_order.ticker,
                    side=p_order.action.value,
                    quantity=p_order.quantity,
                    reference_price=p_order.current_price,
                    execution_price=0.0,
                    gross_notional=0.0,
                    transaction_cost=0.0,
                    slippage_cost=0.0,
                    net_cash_change=0.0,
                    status=OrderStatus.REJECTED,
                    executed_at=datetime.utcnow(),
                    error_message=str(e)
                ))

        # Recalculate weights for simulated holdings
        total_value = sum(h["market_value"] for h in sim_holdings.values())
        for h in sim_holdings.values():
            h["weight"] = h["market_value"] / total_value if total_value > 0 else 0.0

        return PaperExecutionResult(
            evaluation_id=plan.evaluation_id,
            portfolio_id=plan.portfolio_id,
            orders=orders,
            execution_time=datetime.utcnow(),
            total_cost=total_cost,
            simulated_holdings=list(sim_holdings.values())
        )
