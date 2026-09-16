"""Tests for regime orchestration and the complete Phase 3 pipeline."""

from datetime import date, timedelta

import numpy as np
import pandas as pd
import pytest

from quant_engine.regimes.exceptions import InsufficientCoverageError
from quant_engine.regimes.models import (
    CoverageRequirements,
    MarketStressSnapshot,
    StressObservation,
)
from quant_engine.regimes.service import RegimeService
from quant_engine.regimes.threshold import RollingQuantileThreshold
from quant_engine.volatility.aggregation import VolatilityAggregator
from quant_engine.volatility.models import MarketRegime
from quant_engine.volatility.service import VolatilityService

AS_OF_DATE = date(2026, 9, 16)


def snapshot(
    *,
    stress_score: float = 1.1,
    eligible: int = 8,
    total: int = 10,
) -> MarketStressSnapshot:
    return MarketStressSnapshot(
        timestamp=AS_OF_DATE,
        total_asset_count=total,
        eligible_asset_count=eligible,
        model_fit_count=eligible,
        fallback_count=0,
        failed_asset_count=total - eligible,
        excluded_count=total - eligible,
        coverage_ratio=eligible / total,
        fit_coverage_ratio=eligible / total,
        fallback_coverage_ratio=0.0,
        median_conditional_volatility=0.02,
        median_realized_volatility=0.018,
        median_volatility_ratio=stress_score,
        aggregate_volatility=0.02,
        stress_score=stress_score,
        volatility_ratio_iqr=0.2,
    )


def stress_history(scores: list[float]) -> list[StressObservation]:
    start = AS_OF_DATE - timedelta(days=len(scores))
    return [
        StressObservation(
            timestamp=start + timedelta(days=position),
            stress_score=score,
            eligible_asset_count=8,
            coverage_ratio=0.8,
        )
        for position, score in enumerate(scores)
    ]


def test_regime_service_builds_complete_market_state() -> None:
    service = RegimeService(
        threshold_strategy=RollingQuantileThreshold(window_length=5, minimum_history=5)
    )

    state = service.evaluate(snapshot(stress_score=1.3), stress_history([0.8, 0.9, 1.0, 1.1]))

    assert state.as_of_date == AS_OF_DATE
    assert state.total_asset_count == 10
    assert state.eligible_asset_count == 8
    assert state.regime is MarketRegime.HIGH_STRESS
    assert state.distance_to_threshold == pytest.approx(
        state.stress_score - state.adaptive_threshold
    )


def test_regime_service_rejects_insufficient_coverage() -> None:
    service = RegimeService(
        threshold_strategy=RollingQuantileThreshold(window_length=3, minimum_history=3),
        coverage_requirements=CoverageRequirements(
            minimum_asset_count=3,
            minimum_coverage_ratio=0.5,
        ),
    )

    with pytest.raises(InsufficientCoverageError):
        service.evaluate(snapshot(eligible=2, total=10), stress_history([0.8, 0.9]))


def test_regime_service_ignores_future_history() -> None:
    service = RegimeService(
        threshold_strategy=RollingQuantileThreshold(window_length=5, minimum_history=5)
    )
    current = snapshot(stress_score=1.1)
    past = stress_history([0.8, 0.9, 1.0, 1.05])

    baseline = service.evaluate(current, past)
    future = past + [
        StressObservation(
            timestamp=AS_OF_DATE + timedelta(days=1),
            stress_score=100.0,
            eligible_asset_count=10,
            coverage_ratio=1.0,
        )
    ]
    recomputed = service.evaluate(current, future)

    assert recomputed == baseline


def synthetic_returns(seed: int, scale: float) -> pd.Series:
    rng = np.random.default_rng(seed)
    count = 320
    variance = np.empty(count)
    innovations = np.empty(count)
    variance[0] = 0.0001 * scale
    innovations[0] = np.sqrt(variance[0]) * rng.normal()
    for position in range(1, count):
        previous = innovations[position - 1]
        variance[position] = (
            0.000002 * scale
            + 0.05 * previous**2
            + 0.08 * (previous < 0) * previous**2
            + 0.88 * variance[position - 1]
        )
        innovations[position] = np.sqrt(variance[position]) * rng.normal()
    return pd.Series(
        innovations,
        index=pd.date_range(end=AS_OF_DATE, periods=count, freq="B"),
    )


def test_complete_multi_asset_phase3_pipeline() -> None:
    returns_by_ticker = {
        "AAPL": synthetic_returns(11, 0.8),
        "MSFT": synthetic_returns(22, 1.0),
        "NVDA": synthetic_returns(33, 1.2),
    }
    volatility_service = VolatilityService(
        aggregator=VolatilityAggregator(
            coverage_requirements=CoverageRequirements(
                minimum_asset_count=3,
                minimum_coverage_ratio=1.0,
            )
        )
    )
    volatility_result = volatility_service.evaluate(
        returns_by_ticker,
        as_of_date=AS_OF_DATE,
    )
    market_snapshot = volatility_result.market_stress_snapshot
    regime_service = RegimeService(
        threshold_strategy=RollingQuantileThreshold(window_length=10, minimum_history=5),
        coverage_requirements=CoverageRequirements(
            minimum_asset_count=3,
            minimum_coverage_ratio=1.0,
        ),
    )
    state = regime_service.evaluate(
        market_snapshot,
        stress_history([0.85, 0.95, 1.0, 1.1]),
    )

    ratios = [estimate.volatility_ratio for estimate in volatility_result.estimates]
    assert volatility_result.failed_tickers == {}
    assert market_snapshot.stress_score == pytest.approx(float(np.median(ratios)))
    assert state.stress_score == market_snapshot.stress_score
    assert state.regime in set(MarketRegime)
    assert state.total_asset_count == 3
