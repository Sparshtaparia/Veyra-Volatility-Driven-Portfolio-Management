"""Controlled-signal and explainability contracts."""

from datetime import date

from pydantic import BaseModel, ConfigDict, Field

from quant_engine.volatility.models import MarketRegime


class SignalModel(BaseModel):
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
