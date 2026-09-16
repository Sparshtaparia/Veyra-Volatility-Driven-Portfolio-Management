
"""Models for the Phase 5 Composite Risk Engine."""
from enum import Enum
from pydantic import BaseModel, ConfigDict, Field


class RiskState(str, Enum):
    LOW_RISK = "LOW_RISK"
    MODERATE_RISK = "MODERATE_RISK"
    ELEVATED_RISK = "ELEVATED_RISK"
    CRITICAL_RISK = "CRITICAL_RISK"


class RiskComponents(BaseModel):
    """Normalized risk components (0 to 1)."""
    model_config = ConfigDict(extra="forbid")
    
    volatility_exposure: float = Field(ge=0.0, le=1.0)
    concentration: float = Field(ge=0.0, le=1.0)


class CompositeRiskOutput(BaseModel):
    """Output of the Composite Risk Engine for the portfolio."""
    model_config = ConfigDict(extra="forbid")
    
    portfolio_id: str
    composite_score: float = Field(ge=0.0, le=1.0, description="The aggregated risk score (0 to 1)")
    risk_state: RiskState
    components: RiskComponents

