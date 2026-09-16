"""Rebalance planning and deterministic paper execution."""

from quant_engine.portfolio.models import (
    ExecutedTrade,
    RebalanceInstruction,
    TargetWeight,
    TradeSide,
)


class RebalanceEngine:
    def __init__(self, minimum_trade_notional: float = 10.0) -> None:
        if minimum_trade_notional < 0.0:
            raise ValueError("minimum_trade_notional must be non-negative")
        self.minimum_trade_notional = minimum_trade_notional

    def calculate(
        self,
        targets: list[TargetWeight],
        portfolio_value: float,
        prices: dict[str, float],
    ) -> list[RebalanceInstruction]:
        if portfolio_value <= 0.0:
            raise ValueError("portfolio_value must be positive")
        instructions = []
        for target in targets:
            notional = target.weight_change * portfolio_value
            if abs(notional) < self.minimum_trade_notional:
                continue
            price = prices[target.ticker]
            instructions.append(
                RebalanceInstruction(
                    ticker=target.ticker,
                    current_weight=target.current_weight,
                    target_weight=target.target_weight,
                    delta_weight=target.weight_change,
                    notional_change=notional,
                    trade_quantity=abs(notional) / price,
                    side=TradeSide.BUY if notional > 0.0 else TradeSide.SELL,
                    reference_price=price,
                )
            )
        return instructions


class SimulatedExecutor:
    def __init__(self, transaction_cost_bps: float = 5.0, slippage_bps: float = 2.0) -> None:
        if transaction_cost_bps < 0.0 or slippage_bps < 0.0:
            raise ValueError("cost and slippage rates must be non-negative")
        self.transaction_cost_bps = transaction_cost_bps
        self.slippage_bps = slippage_bps

    def execute(self, instructions: list[RebalanceInstruction]) -> list[ExecutedTrade]:
        output = []
        for item in instructions:
            direction = 1.0 if item.side is TradeSide.BUY else -1.0
            execution_price = item.reference_price * (
                1.0 + direction * self.slippage_bps / 10_000.0
            )
            gross = item.trade_quantity * execution_price
            transaction_cost = gross * self.transaction_cost_bps / 10_000.0
            slippage_cost = item.trade_quantity * abs(execution_price - item.reference_price)
            net_cash = (
                -(gross + transaction_cost)
                if item.side is TradeSide.BUY
                else gross - transaction_cost
            )
            output.append(
                ExecutedTrade(
                    ticker=item.ticker,
                    side=item.side,
                    quantity=item.trade_quantity,
                    reference_price=item.reference_price,
                    execution_price=execution_price,
                    gross_notional=gross,
                    transaction_cost=transaction_cost,
                    slippage_cost=slippage_cost,
                    net_cash_change=net_cash,
                )
            )
        return output
