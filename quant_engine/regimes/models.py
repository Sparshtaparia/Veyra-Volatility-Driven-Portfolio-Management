"""Typed contracts for cross-sectional stress and adaptive regimes."""

from __future__ import annotations

from datetime import date
from math import isclose

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from quant_engine.volatility.models import MarketRegime


class RegimeModel(BaseModel):
    model_config = ConfigDict(allow_inf_nan=False, extra="forbid", protected_namespaces=())


class CoverageRequirements(RegimeModel):
    """Minimum breadth required before the market may be classified."""

    minimum_asset_count: int = Field(default=3, gt=0)
    minimum_coverage_ratio: float = Field(default=0.5, gt=0.0, le=1.0)


class StressObservation(RegimeModel):
    """One chronological observation in the market-stress history."""

    timestamp: date
    stress_score: float = Field(gt=0.0)
    eligible_asset_count: int = Field(gt=0)
    coverage_ratio: float = Field(gt=0.0, le=1.0)


class MarketStressSnapshot(RegimeModel):
    """Cross-sectional aggregation of per-asset volatility estimates."""

    timestamp: date
    total_asset_count: int = Field(gt=0)
    eligible_asset_count: int = Field(gt=0)
    model_fit_count: int = Field(ge=0)
    fallback_count: int = Field(ge=0)
    failed_asset_count: int = Field(ge=0)
    excluded_count: int = Field(ge=0)
    coverage_ratio: float = Field(gt=0.0, le=1.0)
    fit_coverage_ratio: float = Field(ge=0.0, le=1.0)
    fallback_coverage_ratio: float = Field(ge=0.0, le=1.0)
    median_conditional_volatility: float = Field(gt=0.0)
    median_realized_volatility: float = Field(gt=0.0)
    median_volatility_ratio: float = Field(gt=0.0)
    aggregate_volatility: float = Field(gt=0.0)
    stress_score: float = Field(gt=0.0)
    volatility_ratio_iqr: float = Field(ge=0.0)

    @model_validator(mode="after")
    def validate_counts_and_ratios(self) -> MarketStressSnapshot:
        if self.eligible_asset_count > self.total_asset_count:
            raise ValueError("eligible_asset_count cannot exceed total_asset_count")
        if self.excluded_count != self.total_asset_count - self.eligible_asset_count:
            raise ValueError("excluded_count must equal total_asset_count - eligible_asset_count")
        classified_count = self.model_fit_count + self.fallback_count + self.failed_asset_count
        if classified_count != self.total_asset_count:
            raise ValueError("fit, fallback, and failed counts must sum to total_asset_count")

        expected = {
            "coverage_ratio": self.eligible_asset_count / self.total_asset_count,
            "fit_coverage_ratio": self.model_fit_count / self.total_asset_count,
            "fallback_coverage_ratio": self.fallback_count / self.total_asset_count,
        }
        for field_name, expected_value in expected.items():
            if not isclose(getattr(self, field_name), expected_value, abs_tol=1e-12):
                raise ValueError(f"{field_name} is inconsistent with asset counts")
        if not isclose(self.aggregate_volatility, self.median_conditional_volatility):
            raise ValueError("aggregate_volatility must equal median_conditional_volatility")
        if not isclose(self.stress_score, self.median_volatility_ratio):
            raise ValueError("stress_score must equal median_volatility_ratio")
        return self

    def to_observation(self) -> StressObservation:
        return StressObservation(
            timestamp=self.timestamp,
            stress_score=self.stress_score,
            eligible_asset_count=self.eligible_asset_count,
            coverage_ratio=self.coverage_ratio,
        )


class ThresholdResult(RegimeModel):
    """Quantile-derived boundaries available at one point in time."""

    timestamp: date
    low_boundary: float = Field(gt=0.0)
    center: float = Field(gt=0.0)
    adaptive_threshold: float = Field(gt=0.0)
    observation_count: int = Field(gt=0)
    window_length: int = Field(gt=0)
    strategy: str

    @field_validator("strategy")
    @classmethod
    def validate_strategy(cls, strategy: str) -> str:
        normalized = strategy.strip()
        if not normalized:
            raise ValueError("strategy must not be empty")
        return normalized

    @model_validator(mode="after")
    def validate_boundary_order(self) -> ThresholdResult:
        if not self.low_boundary <= self.center <= self.adaptive_threshold:
            raise ValueError("regime boundaries must be ordered low <= center <= high")
        return self


class RegimeClassification(RegimeModel):
    """Classification plus its signed distance from the high-stress threshold."""

    regime: MarketRegime
    distance_to_threshold: float
