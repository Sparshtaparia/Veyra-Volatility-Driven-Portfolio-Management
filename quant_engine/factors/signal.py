"""Transparent weighted base-signal construction."""

from quant_engine.factors.models import BaseSignal, FactorSnapshot, SignalConfig


class BaseSignalEngine:
    def __init__(self, config: SignalConfig | None = None) -> None:
        self.config = config or SignalConfig()

    def calculate(self, snapshot: FactorSnapshot) -> BaseSignal:
        factors = set(snapshot.normalized_factors) | set(self.config.weights)
        contributions = {
            factor: self.config.weights.get(factor, 0.0)
            * snapshot.normalized_factors.get(factor, 0.0)
            for factor in sorted(factors)
        }
        return BaseSignal(
            ticker=snapshot.ticker,
            as_of_date=snapshot.as_of_date,
            base_signal=sum(contributions.values()),
            contributions=contributions,
        )
