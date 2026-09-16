"""Regime- and risk-conditioned exposure controller."""

from quant_engine.portfolio.models import ExposureConfig, ExposureState
from quant_engine.volatility.models import MarketRegime


class ExposureController:
    def __init__(self, config: ExposureConfig | None = None) -> None:
        self.config = config or ExposureConfig()

    def calculate(self, regime: MarketRegime, composite_risk: float) -> ExposureState:
        if not 0.0 <= composite_risk <= 1.0:
            raise ValueError("composite_risk must be between 0 and 1")
        regime_factor = self.config.regime_factors[regime]
        risk_factor = max(0.0, 1.0 - self.config.risk_sensitivity * composite_risk)
        exposure = self.config.base_exposure * regime_factor * risk_factor
        exposure = min(self.config.maximum_exposure, max(self.config.minimum_exposure, exposure))
        return ExposureState(
            base_exposure=self.config.base_exposure,
            regime_factor=regime_factor,
            risk_factor=risk_factor,
            target_gross_exposure=exposure,
            target_net_exposure=exposure,
        )
