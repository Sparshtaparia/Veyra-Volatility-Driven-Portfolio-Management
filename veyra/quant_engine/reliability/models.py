"""Reliability contracts and configurable adjustment policy."""

from datetime import date

from pydantic import BaseModel, ConfigDict, Field

from quant_engine.volatility.models import MarketRegime


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
    ticker: str
    as_of_date: date
    base_reliability: float = Field(ge=0.0, le=1.0)
    volatility_adjustment: float = Field(gt=0.0, le=1.0)
    regime_adjustment: float = Field(gt=0.0, le=1.0)
    recent_performance_adjustment: float = Field(gt=0.0)
    reliability_adjustment: float = Field(ge=0.0, le=1.0)
    effective_reliability: float = Field(ge=0.0, le=1.0)
