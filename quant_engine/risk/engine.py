"""Deterministic portfolio risk-state engine."""

from datetime import date

import numpy as np
import pandas as pd

from quant_engine.risk.models import RiskConfig, RiskState


class RiskStateEngine:
    def __init__(self, config: RiskConfig | None = None) -> None:
        self.config = config or RiskConfig()

    def calculate(
        self,
        as_of_date: date,
        *,
        weights: dict[str, float],
        conditional_volatility: dict[str, float],
        return_history: dict[str, pd.Series],
        dollar_volume: dict[str, float],
    ) -> RiskState:
        tickers = sorted(weights)
        volatility = sum(weights[t] * conditional_volatility[t] for t in tickers)
        volatility_risk = self._clip(volatility / self.config.volatility_reference)

        drawdowns = []
        for ticker in tickers:
            returns = return_history[ticker].loc[
                return_history[ticker].index <= pd.Timestamp(as_of_date)
            ]
            wealth = np.exp(returns.cumsum())
            drawdown = (wealth / wealth.cummax() - 1.0).min() if len(wealth) else 0.0
            drawdowns.append(weights[ticker] * abs(float(drawdown)))
        drawdown_risk = self._clip(sum(drawdowns) / self.config.drawdown_reference)

        aligned = pd.concat(
            [return_history[t].rename(t) for t in tickers], axis=1, join="inner"
        ).loc[: pd.Timestamp(as_of_date)]
        if len(tickers) < 2 or aligned.empty:
            correlation_risk = 0.0
        else:
            matrix = aligned.corr().to_numpy(dtype=float)
            upper = matrix[np.triu_indices_from(matrix, k=1)]
            finite = np.abs(upper[np.isfinite(upper)])
            correlation_risk = self._clip(float(finite.mean())) if len(finite) else 0.0

        concentration_risk = self._clip(sum(weight * weight for weight in weights.values()))
        weighted_liquidity = sum(weights[t] * dollar_volume[t] for t in tickers)
        liquidity_risk = self._clip(1.0 - weighted_liquidity / self.config.liquidity_reference)
        components = {
            "volatility_risk": volatility_risk,
            "drawdown_risk": drawdown_risk,
            "correlation_risk": correlation_risk,
            "concentration_risk": concentration_risk,
            "liquidity_risk": liquidity_risk,
        }
        composite = sum(
            self.config.component_weights[name] * value for name, value in components.items()
        )
        return RiskState(as_of_date=as_of_date, composite_risk=composite, **components)

    @staticmethod
    def _clip(value: float) -> float:
        return min(1.0, max(0.0, value))
