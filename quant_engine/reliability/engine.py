"""Explainable reliability computation without machine learning."""

from datetime import date
from math import exp

from quant_engine.reliability.models import ReliabilityConfig, ReliabilityState
from quant_engine.volatility.models import MarketRegime


class ReliabilityEngine:
    def __init__(self, config: ReliabilityConfig | None = None) -> None:
        self.config = config or ReliabilityConfig()

    def calculate(
        self,
        ticker: str,
        as_of_date: date,
        *,
        r_squared: float,
        volatility_ratio: float,
        regime: MarketRegime,
        recent_performance_score: float = 0.0,
    ) -> ReliabilityState:
        if not -1.0 <= recent_performance_score <= 1.0:
            raise ValueError("recent_performance_score must be between -1 and 1")
        base = min(1.0, max(0.0, r_squared))
        volatility = max(
            self.config.minimum_adjustment,
            exp(-self.config.volatility_sensitivity * max(0.0, volatility_ratio - 1.0)),
        )
        regime_adjustment = self.config.regime_adjustments[regime]
        performance = max(
            self.config.minimum_adjustment,
            1.0 + self.config.performance_sensitivity * recent_performance_score,
        )
        reliability_adjustment = min(1.0, base * regime_adjustment * performance)
        return ReliabilityState(
            ticker=ticker,
            as_of_date=as_of_date,
            base_reliability=base,
            volatility_adjustment=volatility,
            regime_adjustment=regime_adjustment,
            recent_performance_adjustment=performance,
            reliability_adjustment=reliability_adjustment,
            effective_reliability=min(1.0, reliability_adjustment * volatility),
        )
