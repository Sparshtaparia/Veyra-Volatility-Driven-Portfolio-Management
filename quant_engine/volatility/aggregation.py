"""Cross-sectional aggregation of per-asset volatility estimates."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import date
from math import isfinite

import numpy as np

from quant_engine.regimes.exceptions import InsufficientCoverageError
from quant_engine.regimes.models import CoverageRequirements, MarketStressSnapshot
from quant_engine.volatility.models import GARCHFitStatus, VolatilityEstimate


class VolatilityAggregator:
    """Build a robust market-stress snapshot using cross-sectional medians."""

    def __init__(
        self,
        *,
        include_fallbacks_in_aggregation: bool = False,
        coverage_requirements: CoverageRequirements | None = None,
    ) -> None:
        self.include_fallbacks_in_aggregation = include_fallbacks_in_aggregation
        self.coverage_requirements = coverage_requirements or CoverageRequirements()

    def aggregate(
        self,
        estimates: Sequence[VolatilityEstimate],
        *,
        total_asset_count: int,
        as_of_date: date,
    ) -> MarketStressSnapshot:
        if total_asset_count <= 0:
            raise ValueError("total_asset_count must be positive")
        if len(estimates) > total_asset_count:
            raise ValueError("estimate count cannot exceed total_asset_count")

        model_fit_count = sum(
            estimate.diagnostics.fit_status is GARCHFitStatus.SUCCESS for estimate in estimates
        )
        fallback_count = sum(
            estimate.diagnostics.fit_status is GARCHFitStatus.FALLBACK for estimate in estimates
        )
        failed_asset_count = total_asset_count - model_fit_count - fallback_count

        eligible = [
            estimate for estimate in estimates if self._is_eligible(estimate, as_of_date=as_of_date)
        ]
        eligible_asset_count = len(eligible)
        coverage_ratio = eligible_asset_count / total_asset_count
        self._validate_coverage(
            eligible_asset_count=eligible_asset_count,
            total_asset_count=total_asset_count,
            coverage_ratio=coverage_ratio,
        )

        conditional_volatilities = np.asarray(
            [estimate.conditional_volatility for estimate in eligible]
        )
        realized_volatilities = np.asarray([estimate.realized_volatility for estimate in eligible])
        volatility_ratios = np.asarray([estimate.volatility_ratio for estimate in eligible])

        median_conditional = float(np.median(conditional_volatilities))
        median_realized = float(np.median(realized_volatilities))
        median_ratio = float(np.median(volatility_ratios))
        ratio_iqr = float(
            np.quantile(volatility_ratios, 0.75) - np.quantile(volatility_ratios, 0.25)
        )

        return MarketStressSnapshot(
            timestamp=as_of_date,
            total_asset_count=total_asset_count,
            eligible_asset_count=eligible_asset_count,
            model_fit_count=model_fit_count,
            fallback_count=fallback_count,
            failed_asset_count=failed_asset_count,
            excluded_count=total_asset_count - eligible_asset_count,
            coverage_ratio=coverage_ratio,
            fit_coverage_ratio=model_fit_count / total_asset_count,
            fallback_coverage_ratio=fallback_count / total_asset_count,
            median_conditional_volatility=median_conditional,
            median_realized_volatility=median_realized,
            median_volatility_ratio=median_ratio,
            aggregate_volatility=median_conditional,
            stress_score=median_ratio,
            volatility_ratio_iqr=ratio_iqr,
        )

    def _is_eligible(self, estimate: VolatilityEstimate, *, as_of_date: date) -> bool:
        if estimate.timestamp != as_of_date:
            return False
        if estimate.diagnostics.fit_status is GARCHFitStatus.SUCCESS:
            pass
        elif (
            estimate.diagnostics.fit_status is GARCHFitStatus.FALLBACK
            and self.include_fallbacks_in_aggregation
        ):
            pass
        else:
            return False

        values = (
            estimate.conditional_volatility,
            estimate.realized_volatility,
            estimate.volatility_ratio,
        )
        return all(isfinite(value) and value > 0.0 for value in values)

    def _validate_coverage(
        self,
        *,
        eligible_asset_count: int,
        total_asset_count: int,
        coverage_ratio: float,
    ) -> None:
        requirements = self.coverage_requirements
        if (
            eligible_asset_count < requirements.minimum_asset_count
            or coverage_ratio < requirements.minimum_coverage_ratio
        ):
            raise InsufficientCoverageError(
                eligible_asset_count=eligible_asset_count,
                total_asset_count=total_asset_count,
                minimum_asset_count=requirements.minimum_asset_count,
                minimum_coverage_ratio=requirements.minimum_coverage_ratio,
            )
