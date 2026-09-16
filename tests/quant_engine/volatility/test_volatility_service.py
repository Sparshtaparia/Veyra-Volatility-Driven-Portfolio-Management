"""Tests for per-asset volatility orchestration."""

from datetime import date

import numpy as np
import pandas as pd
import pytest

from quant_engine.regimes.exceptions import InsufficientCoverageError
from quant_engine.regimes.models import CoverageRequirements
from quant_engine.volatility.aggregation import VolatilityAggregator
from quant_engine.volatility.exceptions import InvalidReturnsError
from quant_engine.volatility.models import (
    GARCHConvergenceStatus,
    GARCHDiagnostics,
    GARCHFitStatus,
    GARCHParameters,
    VolatilityEstimate,
)
from quant_engine.volatility.service import VolatilityService

AS_OF_DATE = date(2026, 9, 16)


class FakeEngine:
    def __init__(
        self,
        failures: set[str] | None = None,
        fallbacks: set[str] | None = None,
    ) -> None:
        self.failures = failures or set()
        self.fallbacks = fallbacks or set()

    def fit(
        self,
        ticker: str,
        returns: pd.Series,
        as_of_date: date,
    ) -> VolatilityEstimate:
        if ticker in self.failures:
            raise InvalidReturnsError(f"invalid history for {ticker}")
        status = GARCHFitStatus.FALLBACK if ticker in self.fallbacks else GARCHFitStatus.SUCCESS
        ratio = float(returns.iloc[-1])
        conditional_volatility = 0.02
        return VolatilityEstimate(
            ticker=ticker,
            timestamp=as_of_date,
            conditional_variance=conditional_volatility**2,
            conditional_volatility=conditional_volatility,
            forecast_volatility=0.021,
            realized_volatility=conditional_volatility / ratio,
            volatility_ratio=ratio,
            parameters=(
                GARCHParameters(omega=0.000001, alpha=0.05, gamma=0.08, beta=0.85)
                if status is GARCHFitStatus.SUCCESS
                else None
            ),
            diagnostics=GARCHDiagnostics(
                fit_status=status,
                convergence_status=(
                    GARCHConvergenceStatus.CONVERGED
                    if status is GARCHFitStatus.SUCCESS
                    else GARCHConvergenceStatus.NOT_APPLICABLE
                ),
                observation_count=len(returns),
            ),
        )


def returns_map(*tickers: str) -> dict[str, pd.Series]:
    index = pd.date_range("2026-09-01", periods=12, freq="B")
    return {
        ticker: pd.Series(np.linspace(0.8 + position * 0.1, 1.0 + position * 0.1, 12), index=index)
        for position, ticker in enumerate(tickers)
    }


def aggregator(*, include_fallbacks: bool = False) -> VolatilityAggregator:
    return VolatilityAggregator(
        include_fallbacks_in_aggregation=include_fallbacks,
        coverage_requirements=CoverageRequirements(
            minimum_asset_count=1,
            minimum_coverage_ratio=0.25,
        ),
    )


def test_service_collects_multiple_valid_estimates() -> None:
    service = VolatilityService(engine=FakeEngine(), aggregator=aggregator())

    result = service.evaluate(returns_map("A", "B", "C"), as_of_date=AS_OF_DATE)

    assert len(result.estimates) == 3
    assert len(result.successful_estimates) == 3
    assert result.fallback_estimates == []
    assert result.failed_tickers == {}
    assert result.market_stress_snapshot.eligible_asset_count == 3
    assert result.market_stress_snapshot.stress_score == pytest.approx(1.1)


def test_individual_ticker_failure_does_not_abort_evaluation() -> None:
    service = VolatilityService(engine=FakeEngine(failures={"B"}), aggregator=aggregator())

    result = service.evaluate(returns_map("A", "B", "C"), as_of_date=AS_OF_DATE)

    assert len(result.estimates) == 2
    assert set(result.failed_tickers) == {"B"}
    assert result.market_stress_snapshot.failed_asset_count == 1


def test_multiple_failures_can_trigger_coverage_safety() -> None:
    strict_aggregator = VolatilityAggregator(
        coverage_requirements=CoverageRequirements(
            minimum_asset_count=2,
            minimum_coverage_ratio=0.5,
        )
    )
    service = VolatilityService(
        engine=FakeEngine(failures={"B", "C", "D"}),
        aggregator=strict_aggregator,
    )

    with pytest.raises(InsufficientCoverageError):
        service.evaluate(returns_map("A", "B", "C", "D"), as_of_date=AS_OF_DATE)


def test_service_respects_configured_fallback_policy() -> None:
    inputs = returns_map("FIT", "FALLBACK")
    engine = FakeEngine(fallbacks={"FALLBACK"})

    excluded = VolatilityService(engine=engine, aggregator=aggregator()).evaluate(
        inputs,
        as_of_date=AS_OF_DATE,
    )
    included = VolatilityService(
        engine=engine,
        aggregator=aggregator(include_fallbacks=True),
    ).evaluate(inputs, as_of_date=AS_OF_DATE)

    assert excluded.market_stress_snapshot.eligible_asset_count == 1
    assert included.market_stress_snapshot.eligible_asset_count == 2
    assert len(included.fallback_estimates) == 1
