"""Models for the Phase 5 Reliability Engine."""
from enum import Enum
from pydantic import BaseModel, ConfigDict, Field


class ReliabilityState(str, Enum):
    HIGH = "HIGH"
    MODERATE = "MODERATE"
    LOW = "LOW"


class ReliabilityOutput(BaseModel):
    """Output of the Reliability service for a specific asset."""
    model_config = ConfigDict(extra="forbid")
    
    ticker: str
    sigma_it: float = Field(ge=0.0, description="The asset's volatility state")
    kappa: float = Field(ge=0.0, description="The kappa parameter used")
    reliability_score: float = Field(ge=0.0, le=1.0, description="The bounded reliability score W_i,t")
    reliability_state: ReliabilityState
