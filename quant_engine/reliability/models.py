"""Reliability contracts for the persisted and decision-level pipelines."""

from datetime import date
from enum import Enum
from typing import ClassVar

from pydantic import BaseModel, ConfigDict, Field

from quant_engine.volatility.models import MarketRegime


class ReliabilityLevel(str, Enum):
    """Discrete level used by the newer decision-control pipeline."""

    HIGH = "HIGH"
    MODERATE = "MODERATE"
    LOW = "LOW"


class ReliabilityModel(BaseModel):
    model_config = ConfigDict(allow_inf_nan=False, extra="forbid")


class ReliabilityConfig(ReliabilityModel):
    volatility_sensitivity: float = Field(default=0.5, ge=0.0)
    performance_sensitivity: float = Field(default=0.25, ge=0.0)
    minimum_adjustment: float = Field(default=0.25, gt=0.0, le=1.0)
    regime_adjustments: dict[MarketRegime, float] = Field(
        default_factory=lambda: {
            MarketRegime.LOW_VOL: 1.0,
            MarketRegime.NORMAL: 1.0,
            MarketRegime.ELEVATED: 0.75,
            MarketRegime.HIGH_STRESS: 0.5,
        }
    )


class ReliabilityState(ReliabilityModel):
    """Structured Phase 4 reliability state persisted with an evaluation."""

    # Compatibility constants for callers of the newer discrete pipeline.
    HIGH: ClassVar[ReliabilityLevel] = ReliabilityLevel.HIGH
    MODERATE: ClassVar[ReliabilityLevel] = ReliabilityLevel.MODERATE
    LOW: ClassVar[ReliabilityLevel] = ReliabilityLevel.LOW

    ticker: str
    as_of_date: date
    base_reliability: float = Field(ge=0.0, le=1.0)
    volatility_adjustment: float = Field(gt=0.0, le=1.0)
    regime_adjustment: float = Field(gt=0.0, le=1.0)
    recent_performance_adjustment: float = Field(gt=0.0)
    reliability_adjustment: float = Field(ge=0.0, le=1.0)
    effective_reliability: float = Field(ge=0.0, le=1.0)


class ReliabilityOutput(BaseModel):
    """Discrete reliability output used by decision-level controls."""

    model_config = ConfigDict(extra="forbid")

    ticker: str
    sigma_it: float = Field(ge=0.0, description="The asset's volatility state")
    kappa: float = Field(ge=0.0, description="The kappa parameter used")
    reliability_score: float = Field(
        ge=0.0, le=1.0, description="The bounded reliability score W_i,t"
    )
    reliability_state: ReliabilityLevel
