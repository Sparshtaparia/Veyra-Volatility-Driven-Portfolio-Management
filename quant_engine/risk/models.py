"""Risk contracts for persisted and decision-level pipelines."""

from datetime import date
from enum import Enum
from typing import ClassVar

from pydantic import BaseModel, ConfigDict, Field, model_validator


class RiskLevel(str, Enum):
    LOW_RISK = "LOW_RISK"
    MODERATE_RISK = "MODERATE_RISK"
    ELEVATED_RISK = "ELEVATED_RISK"
    CRITICAL_RISK = "CRITICAL_RISK"


class RiskModel(BaseModel):
    model_config = ConfigDict(allow_inf_nan=False, extra="forbid")


class RiskConfig(RiskModel):
    volatility_reference: float = Field(default=0.04, gt=0.0)
    drawdown_reference: float = Field(default=0.20, gt=0.0)
    liquidity_reference: float = Field(default=10_000_000.0, gt=0.0)
    component_weights: dict[str, float] = Field(
        default_factory=lambda: {
            "volatility_risk": 0.25,
            "drawdown_risk": 0.20,
            "correlation_risk": 0.20,
            "concentration_risk": 0.20,
            "liquidity_risk": 0.15,
        }
    )

    @model_validator(mode="after")
    def validate_weights(self) -> "RiskConfig":
        expected = {
            "volatility_risk",
            "drawdown_risk",
            "correlation_risk",
            "concentration_risk",
            "liquidity_risk",
        }
        if set(self.component_weights) != expected:
            raise ValueError("component_weights must define every risk component")
        if any(weight < 0.0 for weight in self.component_weights.values()):
            raise ValueError("risk weights must be non-negative")
        if abs(sum(self.component_weights.values()) - 1.0) > 1e-10:
            raise ValueError("risk weights must sum to 1")
        return self


class RiskState(RiskModel):
    """Structured Phase 4 portfolio risk state."""

    # Compatibility constants for the newer decision-control pipeline.
    LOW_RISK: ClassVar[RiskLevel] = RiskLevel.LOW_RISK
    MODERATE_RISK: ClassVar[RiskLevel] = RiskLevel.MODERATE_RISK
    ELEVATED_RISK: ClassVar[RiskLevel] = RiskLevel.ELEVATED_RISK
    CRITICAL_RISK: ClassVar[RiskLevel] = RiskLevel.CRITICAL_RISK

    as_of_date: date
    volatility_risk: float = Field(ge=0.0, le=1.0)
    drawdown_risk: float = Field(ge=0.0, le=1.0)
    correlation_risk: float = Field(ge=0.0, le=1.0)
    concentration_risk: float = Field(ge=0.0, le=1.0)
    liquidity_risk: float = Field(ge=0.0, le=1.0)
    composite_risk: float = Field(ge=0.0, le=1.0)


class RiskComponents(BaseModel):
    model_config = ConfigDict(extra="forbid")

    volatility_exposure: float = Field(ge=0.0, le=1.0)
    concentration: float = Field(ge=0.0, le=1.0)


class CompositeRiskOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    portfolio_id: str
    composite_score: float = Field(ge=0.0, le=1.0)
    risk_state: RiskLevel
    components: RiskComponents
