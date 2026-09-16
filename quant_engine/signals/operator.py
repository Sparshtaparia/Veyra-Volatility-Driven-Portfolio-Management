"""Transparent deterministic state-coupled operator."""

from datetime import date

from quant_engine.signals.models import ControlledSignal, OperatorConfig


class StateCoupledOperator:
    def __init__(self, config: OperatorConfig | None = None) -> None:
        self.config = config or OperatorConfig()

    def apply(
        self,
        ticker: str,
        as_of_date: date,
        *,
        base_signal: float,
        volatility_adjustment: float,
        reliability_adjustment: float,
        composite_risk: float,
    ) -> ControlledSignal:
        risk_adjustment = max(
            self.config.minimum_risk_adjustment,
            1.0 - self.config.risk_aversion * composite_risk,
        )
        risk_adjustment = min(1.0, risk_adjustment)
        controlled = base_signal * volatility_adjustment * reliability_adjustment * risk_adjustment
        return ControlledSignal(
            ticker=ticker,
            as_of_date=as_of_date,
            base_signal=base_signal,
            volatility_adjustment=volatility_adjustment,
            reliability_adjustment=reliability_adjustment,
            risk_adjustment=risk_adjustment,
            controlled_signal=controlled,
        )
