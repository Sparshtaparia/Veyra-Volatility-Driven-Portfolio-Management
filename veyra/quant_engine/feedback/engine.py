"""Transparent deterministic feedback controller."""

from quant_engine.feedback.models import (
    FeedbackConfig,
    FeedbackOutcome,
    FeedbackUpdate,
    SystemState,
)


class FeedbackController:
    def __init__(self, config: FeedbackConfig | None = None) -> None:
        self.config = config or FeedbackConfig()

    def update(
        self,
        state: SystemState,
        controlled_signal: float,
        outcome: FeedbackOutcome,
    ) -> FeedbackUpdate:
        rate = self.config.learning_rate
        volatility_level = (1.0 - rate) * state.volatility_distribution_level + rate * max(
            outcome.realized_volatility, 1e-12
        )
        threshold = (1.0 - rate) * state.adaptive_threshold + rate * max(
            outcome.realized_volatility / max(volatility_level, 1e-12), 1e-12
        )
        reliability = state.reliability_multiplier * (1.0 + rate * outcome.signal_accuracy)
        reliability = min(1.0, max(self.config.minimum_reliability_multiplier, reliability))
        observed_risk = min(1.0, outcome.drawdown + outcome.realized_volatility)
        risk_limit = min(1.0, max(0.01, (1.0 - rate) * state.risk_limit + rate * observed_risk))
        exposure_limit = state.exposure_limit * (1.0 - rate * observed_risk)
        if outcome.portfolio_return > 0.0 and outcome.signal_accuracy > 0.0:
            exposure_limit *= 1.0 + rate * min(outcome.portfolio_return, 1.0)
        exposure_limit = min(
            self.config.maximum_exposure_limit,
            max(self.config.minimum_exposure_limit, exposure_limit),
        )
        updated = SystemState(
            as_of_date=outcome.observation_date,
            volatility_distribution_level=volatility_level,
            adaptive_threshold=threshold,
            reliability_multiplier=reliability,
            risk_limit=risk_limit,
            exposure_limit=exposure_limit,
            portfolio_value=max(
                0.0,
                state.portfolio_value * (1.0 + outcome.portfolio_return) - outcome.transaction_cost,
            ),
        )
        return FeedbackUpdate(
            previous_state=state,
            controlled_signal=controlled_signal,
            outcome=outcome,
            updated_state=updated,
        )
