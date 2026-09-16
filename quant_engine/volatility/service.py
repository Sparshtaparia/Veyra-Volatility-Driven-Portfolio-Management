"""Orchestration of per-asset fits and cross-sectional volatility aggregation."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date, datetime

import pandas as pd

from quant_engine.regimes.models import MarketStressSnapshot
from quant_engine.volatility.aggregation import VolatilityAggregator
from quant_engine.volatility.exceptions import VolatilityEngineError
from quant_engine.volatility.gjr_garch import GJRGarchEngine
from quant_engine.volatility.models import GARCHFitStatus, VolatilityEstimate


@dataclass(frozen=True)
class VolatilityServiceResult:
    estimates: list[VolatilityEstimate]
    failed_tickers: dict[str, str]
    market_stress_snapshot: MarketStressSnapshot

    @property
    def successful_estimates(self) -> list[VolatilityEstimate]:
        return [
            estimate
            for estimate in self.estimates
            if estimate.diagnostics.fit_status is GARCHFitStatus.SUCCESS
        ]

    @property
    def fallback_estimates(self) -> list[VolatilityEstimate]:
        return [
            estimate
            for estimate in self.estimates
            if estimate.diagnostics.fit_status is GARCHFitStatus.FALLBACK
        ]


class VolatilityService:
    """Fit each ticker independently, then aggregate the surviving estimates."""

    def __init__(
        self,
        engine: GJRGarchEngine | None = None,
        aggregator: VolatilityAggregator | None = None,
    ) -> None:
        self.engine = engine or GJRGarchEngine()
        self.aggregator = aggregator or VolatilityAggregator()

    def evaluate(
        self,
        returns_by_ticker: Mapping[str, pd.Series],
        *,
        as_of_date: date | datetime,
    ) -> VolatilityServiceResult:
        if not returns_by_ticker:
            raise ValueError("returns_by_ticker must not be empty")

        estimates: list[VolatilityEstimate] = []
        failed_tickers: dict[str, str] = {}
        for ticker, returns in returns_by_ticker.items():
            try:
                estimates.append(self.engine.fit(ticker, returns, as_of_date))
            except VolatilityEngineError as exc:
                failed_tickers[ticker] = str(exc)

        snapshot = self.aggregator.aggregate(
            estimates,
            total_asset_count=len(returns_by_ticker),
            as_of_date=pd.Timestamp(as_of_date).date(),
        )
        return VolatilityServiceResult(
            estimates=estimates,
            failed_tickers=failed_tickers,
            market_stress_snapshot=snapshot,
        )
