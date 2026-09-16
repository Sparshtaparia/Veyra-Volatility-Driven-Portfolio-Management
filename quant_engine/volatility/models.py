"""
Domain contracts for Phase 3 volatility estimates and market regimes.

These models contain no fitting or persistence logic. They define the validated
boundary between the future GJR-GARCH implementation and its consumers.
"""

from __future__ import annotations

from datetime import date
from enum import Enum
from math import isclose

from pydantic import AliasChoices, BaseModel, ConfigDict, Field, field_validator, model_validator


class GARCHFitStatus(str, Enum):
    """Outcome of attempting to produce an asset-level volatility estimate."""

    SUCCESS = "SUCCESS"
    FALLBACK = "FALLBACK"
    FAILED = "FAILED"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"


class GARCHConvergenceStatus(str, Enum):
    """Optimizer convergence state for a GJR-GARCH fit."""

    CONVERGED = "CONVERGED"
    NOT_CONVERGED = "NOT_CONVERGED"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class MarketRegime(str, Enum):
    """Market-wide volatility regime derived from the adaptive threshold."""

    LOW_VOL = "LOW_VOL"
    NORMAL = "NORMAL"
    ELEVATED = "ELEVATED"
    HIGH_STRESS = "HIGH_STRESS"


class VolatilityModel(BaseModel):
    """Shared validation policy for Phase 3 value objects."""

    model_config = ConfigDict(allow_inf_nan=False, extra="forbid")


class GARCHParameters(VolatilityModel):
    """Estimated parameters for a GJR-GARCH(1,1) process."""

    omega: float = Field(gt=0.0)
    alpha: float = Field(ge=0.0)
    gamma: float
    beta: float = Field(ge=0.0)

    @property
    def persistence(self) -> float:
        """Expected-shock persistence under the model's symmetric Normal innovations."""

        return self.alpha + self.beta + (self.gamma / 2.0)

    @model_validator(mode="after")
    def validate_parameter_constraints(self) -> GARCHParameters:
        if self.alpha + self.gamma < 0.0:
            raise ValueError("alpha + gamma must be >= 0")

        if self.persistence >= 1.0:
            raise ValueError(
                "GJR-GARCH persistence (alpha + beta + gamma / 2) must be < 1"
            )
        return self


class GARCHDiagnostics(VolatilityModel):
    """Fit metadata kept separate from the numerical volatility estimate."""

    fit_status: GARCHFitStatus
    convergence_status: GARCHConvergenceStatus
    observation_count: int = Field(ge=0)
    log_likelihood: float | None = None
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)

    @field_validator("warnings", "errors")
    @classmethod
    def validate_messages(cls, messages: list[str]) -> list[str]:
        normalized = [message.strip() for message in messages]
        if any(not message for message in normalized):
            raise ValueError("diagnostic messages must not be empty")
        return normalized


class VolatilityEstimate(VolatilityModel):
    """Daily asset-level volatility output produced without lookahead."""

    ticker: str
    timestamp: date
    conditional_variance: float = Field(ge=0.0)
    conditional_volatility: float = Field(ge=0.0)
    forecast_volatility: float = Field(ge=0.0)
    realized_volatility: float = Field(ge=0.0)
    volatility_ratio: float = Field(ge=0.0)
    parameters: GARCHParameters | None = None
    diagnostics: GARCHDiagnostics

    @field_validator("ticker")
    @classmethod
    def normalize_ticker(cls, ticker: str) -> str:
        normalized = ticker.strip().upper()
        if not normalized:
            raise ValueError("ticker must not be empty")
        return normalized

    @model_validator(mode="after")
    def validate_estimate_consistency(self) -> VolatilityEstimate:
        expected_variance = self.conditional_volatility**2
        if not isclose(
            self.conditional_variance,
            expected_variance,
            rel_tol=1e-6,
            abs_tol=1e-12,
        ):
            raise ValueError("conditional_variance must equal conditional_volatility squared")

        if self.diagnostics.fit_status is GARCHFitStatus.SUCCESS and self.parameters is None:
            raise ValueError("parameters are required for a successful GJR-GARCH fit")
        return self


class MarketVolatilityState(VolatilityModel):
    """Cross-sectional volatility state and its threshold-derived regime."""

    as_of_date: date = Field(
        validation_alias=AliasChoices("as_of_date", "timestamp")
    )
    total_asset_count: int = Field(
        gt=0,
        validation_alias=AliasChoices("total_asset_count", "number_of_assets"),
    )
    eligible_asset_count: int | None = Field(default=None, ge=0)
    model_fit_count: int | None = Field(default=None, ge=0)
    fallback_count: int = Field(default=0, ge=0)
    failed_asset_count: int = Field(default=0, ge=0)
    excluded_count: int | None = Field(default=None, ge=0)
    coverage_ratio: float | None = Field(default=None, ge=0.0, le=1.0)
    aggregate_volatility: float = Field(ge=0.0)
    median_volatility_ratio: float = Field(ge=0.0)
    stress_score: float = Field(ge=0.0)
    adaptive_threshold: float = Field(
        ge=0.0,
        validation_alias=AliasChoices("adaptive_threshold", "threshold"),
    )
    regime: MarketRegime
    distance_to_threshold: float | None = None

    @property
    def timestamp(self) -> date:
        """Backward-compatible name used by the Phase 3A contract."""

        return self.as_of_date

    @property
    def number_of_assets(self) -> int:
        """Backward-compatible name used by the Phase 3A contract."""

        return self.total_asset_count

    @property
    def threshold(self) -> float:
        """Backward-compatible name used by the Phase 3A contract."""

        return self.adaptive_threshold

    @model_validator(mode="after")
    def validate_state(self) -> MarketVolatilityState:
        if self.eligible_asset_count is None:
            self.eligible_asset_count = self.total_asset_count
        if self.model_fit_count is None:
            self.model_fit_count = self.eligible_asset_count
        if self.excluded_count is None:
            self.excluded_count = self.total_asset_count - self.eligible_asset_count
        if self.coverage_ratio is None:
            self.coverage_ratio = self.eligible_asset_count / self.total_asset_count
        if self.distance_to_threshold is None:
            self.distance_to_threshold = self.stress_score - self.adaptive_threshold

        counts = (
            self.eligible_asset_count,
            self.model_fit_count,
            self.fallback_count,
            self.failed_asset_count,
            self.excluded_count,
        )
        if any(count > self.total_asset_count for count in counts):
            raise ValueError("market-state counts cannot exceed total_asset_count")
        classified_count = self.model_fit_count + self.fallback_count + self.failed_asset_count
        if classified_count != self.total_asset_count:
            raise ValueError("fit, fallback, and failed counts must sum to total_asset_count")
        if self.excluded_count != self.total_asset_count - self.eligible_asset_count:
            raise ValueError("excluded_count must equal total_asset_count - eligible_asset_count")
        expected_coverage = self.eligible_asset_count / self.total_asset_count
        if not isclose(self.coverage_ratio, expected_coverage, abs_tol=1e-12):
            raise ValueError("coverage_ratio must equal eligible_asset_count / total_asset_count")

        is_high_stress = self.stress_score >= self.adaptive_threshold
        if (self.regime is MarketRegime.HIGH_STRESS) is not is_high_stress:
            expected = "HIGH_STRESS" if is_high_stress else "a non-HIGH_STRESS regime"
            raise ValueError(
                f"regime must be {expected} when stress_score is {self.stress_score} "
                f"and adaptive_threshold is {self.adaptive_threshold}"
            )
        return self
