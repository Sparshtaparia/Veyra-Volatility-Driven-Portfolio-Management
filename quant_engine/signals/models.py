
"""Typed, deterministic Phase 4 base-signal contracts."""
from datetime import date
from enum import Enum
from pydantic import BaseModel, ConfigDict, Field, field_validator

from quant_engine.volatility.models import MarketRegime


class SignalDirection(str, Enum):
    BUY = "BUY"
    SELL = "SELL"
    NEUTRAL = "NEUTRAL"


class SignalComponents(BaseModel):
    model_config = ConfigDict(extra="forbid")
    rsi: float = Field(ge=-1.0, le=1.0)
    macd_momentum: float = Field(ge=-1.0, le=1.0)
    band_width_penalty: float = Field(ge=0.0, le=1.0)


class BaseSignal(BaseModel):
    model_config = ConfigDict(extra="forbid")
    ticker: str
    timestamp: date
    components: SignalComponents
    composite_signal: float = Field(ge=-1.0, le=1.0)
    direction: SignalDirection

    @field_validator("ticker")
    @classmethod
    def normalize_ticker(cls, value: str) -> str:
        value = value.strip().upper()
        if not value:
            raise ValueError("ticker must not be empty")
        return value


class SignalModel(BaseModel):
    """Base contract for Phase 4 controlled-signal state."""

    model_config = ConfigDict(allow_inf_nan=False, extra="forbid")


class OperatorConfig(SignalModel):
    risk_aversion: float = Field(default=1.0, ge=0.0)
    minimum_risk_adjustment: float = Field(default=0.0, ge=0.0, le=1.0)


class ControlledSignal(SignalModel):
    ticker: str
    as_of_date: date
    base_signal: float
    volatility_adjustment: float = Field(ge=0.0, le=1.0)
    reliability_adjustment: float = Field(ge=0.0, le=1.0)
    risk_adjustment: float = Field(ge=0.0, le=1.0)
    controlled_signal: float


class ExplainabilityPayload(SignalModel):
    ticker: str
    as_of_date: date
    raw_factors: dict[str, float]
    normalized_factors: dict[str, float]
    factor_contributions: dict[str, float]
    base_signal: float
    effective_reliability: float
    conditional_volatility: float
    volatility_ratio: float
    market_stress: float
    regime: MarketRegime
    risk_contribution: float
    volatility_adjustment: float
    reliability_adjustment: float
    risk_adjustment: float
    controlled_signal: float
