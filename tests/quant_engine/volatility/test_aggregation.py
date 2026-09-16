"""Tests for cross-sectional volatility aggregation."""

from datetime import date

import pytest

from quant_engine.regimes.exceptions import InsufficientCoverageError
from quant_engine.regimes.models import CoverageRequirements
from quant_engine.volatility.aggregation import VolatilityAggregator
from quant_engine.volatility.models import (
    GARCHConvergenceStatus,
    GARCHDiagnostics,
    GARCHFitStatus,
    GARCHParameters,
    VolatilityEstimate,
)

AS_OF_DATE = date(2026, 9, 16)


def estimate(
    ticker: str,
    ratio: float,
    *,
    status: GARCHFitStatus = GARCHFitStatus.SUCCESS,
    conditional_volatility: float = 0.02,
    timestamp: date = AS_OF_DATE,
) -> VolatilityEstimate:
    realized_volatility = conditional_volatility / ratio
    return VolatilityEstimate(
        ticker=ticker,
        timestamp=timestamp,
        conditional_variance=conditional_volatility**2,
        conditional_volatility=conditional_volatility,
        forecast_volatility=conditional_volatility,
        realized_volatility=realized_volatility,
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
            observation_count=300,
        ),
    )


def permissive_coverage() -> CoverageRequirements:
    return CoverageRequirements(minimum_asset_count=1, minimum_coverage_ratio=0.1)


def test_cross_section_uses_median_ratio_and_is_robust_to_outlier() -> None:
    estimates = [
        estimate("A", 0.9, conditional_volatility=0.018),
        estimate("B", 1.0, conditional_volatility=0.020),
        estimate("C", 1.1, conditional_volatility=0.022),
        estimate("OUTLIER", 100.0, conditional_volatility=2.0),
    ]
    aggregator = VolatilityAggregator(coverage_requirements=permissive_coverage())

    snapshot = aggregator.aggregate(
        estimates,
        total_asset_count=4,
        as_of_date=AS_OF_DATE,
    )

    assert snapshot.median_volatility_ratio == pytest.approx(1.05)
    assert snapshot.stress_score == snapshot.median_volatility_ratio
    assert snapshot.aggregate_volatility == pytest.approx(0.021)
    assert snapshot.volatility_ratio_iqr < 30.0


def test_invalid_and_wrong_timestamp_estimates_are_excluded() -> None:
    invalid = estimate("INVALID", 1.0).model_copy(update={"volatility_ratio": float("nan")})
    wrong_date = estimate("OLD", 1.0, timestamp=date(2026, 9, 15))
    aggregator = VolatilityAggregator(coverage_requirements=permissive_coverage())

    snapshot = aggregator.aggregate(
        [estimate("VALID", 1.1), invalid, wrong_date],
        total_asset_count=3,
        as_of_date=AS_OF_DATE,
    )

    assert snapshot.eligible_asset_count == 1
    assert snapshot.excluded_count == 2
    assert snapshot.stress_score == pytest.approx(1.1)


def test_fallbacks_are_excluded_by_default_and_recorded() -> None:
    aggregator = VolatilityAggregator(coverage_requirements=permissive_coverage())

    snapshot = aggregator.aggregate(
        [estimate("FIT", 1.2), estimate("FALLBACK", 0.4, status=GARCHFitStatus.FALLBACK)],
        total_asset_count=3,
        as_of_date=AS_OF_DATE,
    )

    assert snapshot.model_fit_count == 1
    assert snapshot.fallback_count == 1
    assert snapshot.failed_asset_count == 1
    assert snapshot.eligible_asset_count == 1
    assert snapshot.excluded_count == 2
    assert snapshot.fit_coverage_ratio == pytest.approx(1 / 3)
    assert snapshot.fallback_coverage_ratio == pytest.approx(1 / 3)


def test_fallbacks_can_be_included_explicitly() -> None:
    aggregator = VolatilityAggregator(
        include_fallbacks_in_aggregation=True,
        coverage_requirements=permissive_coverage(),
    )

    snapshot = aggregator.aggregate(
        [estimate("FIT", 1.2), estimate("FALLBACK", 0.8, status=GARCHFitStatus.FALLBACK)],
        total_asset_count=2,
        as_of_date=AS_OF_DATE,
    )

    assert snapshot.eligible_asset_count == 2
    assert snapshot.stress_score == pytest.approx(1.0)
    assert snapshot.coverage_ratio == 1.0


def test_insufficient_cross_sectional_coverage_is_explicit() -> None:
    aggregator = VolatilityAggregator(
        coverage_requirements=CoverageRequirements(
            minimum_asset_count=2,
            minimum_coverage_ratio=0.75,
        )
    )

    with pytest.raises(InsufficientCoverageError) as error:
        aggregator.aggregate(
            [estimate("ONLY", 1.0)],
            total_asset_count=4,
            as_of_date=AS_OF_DATE,
        )

    assert error.value.eligible_asset_count == 1
    assert error.value.total_asset_count == 4
