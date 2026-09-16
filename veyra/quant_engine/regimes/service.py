"""Orchestration from a market-stress snapshot to a volatility regime."""

from __future__ import annotations

from collections.abc import Sequence

from quant_engine.regimes.classifier import RegimeClassifier
from quant_engine.regimes.exceptions import InsufficientCoverageError
from quant_engine.regimes.models import (
    CoverageRequirements,
    MarketStressSnapshot,
    StressObservation,
)
from quant_engine.regimes.threshold import RollingQuantileThreshold, ThresholdStrategy
from quant_engine.volatility.models import MarketVolatilityState


class RegimeService:
    def __init__(
        self,
        threshold_strategy: ThresholdStrategy | None = None,
        classifier: RegimeClassifier | None = None,
        coverage_requirements: CoverageRequirements | None = None,
    ) -> None:
        self.threshold_strategy = threshold_strategy or RollingQuantileThreshold()
        self.classifier = classifier or RegimeClassifier()
        self.coverage_requirements = coverage_requirements or CoverageRequirements()

    def evaluate(
        self,
        current: MarketStressSnapshot,
        history: Sequence[StressObservation],
    ) -> MarketVolatilityState:
        self._validate_coverage(current)
        observations = [item for item in history if item.timestamp < current.timestamp]
        observations.append(current.to_observation())
        thresholds = self.threshold_strategy.calculate(observations, current.timestamp)
        classification = self.classifier.classify(current.stress_score, thresholds)

        return MarketVolatilityState(
            as_of_date=current.timestamp,
            total_asset_count=current.total_asset_count,
            eligible_asset_count=current.eligible_asset_count,
            model_fit_count=current.model_fit_count,
            fallback_count=current.fallback_count,
            failed_asset_count=current.failed_asset_count,
            excluded_count=current.excluded_count,
            coverage_ratio=current.coverage_ratio,
            aggregate_volatility=current.aggregate_volatility,
            median_volatility_ratio=current.median_volatility_ratio,
            stress_score=current.stress_score,
            adaptive_threshold=thresholds.adaptive_threshold,
            regime=classification.regime,
            distance_to_threshold=classification.distance_to_threshold,
        )

    def _validate_coverage(self, snapshot: MarketStressSnapshot) -> None:
        requirements = self.coverage_requirements
        if (
            snapshot.eligible_asset_count < requirements.minimum_asset_count
            or snapshot.coverage_ratio < requirements.minimum_coverage_ratio
        ):
            raise InsufficientCoverageError(
                eligible_asset_count=snapshot.eligible_asset_count,
                total_asset_count=snapshot.total_asset_count,
                minimum_asset_count=requirements.minimum_asset_count,
                minimum_coverage_ratio=requirements.minimum_coverage_ratio,
            )
