"""State-coupled Phase 4 decision contracts."""
from enum import Enum
from pydantic import BaseModel, ConfigDict, Field
from quant_engine.signal_control.models import RegulatedSignal
from quant_engine.signals.models import SignalDirection
from quant_engine.volatility.models import MarketRegime


from quant_engine.reliability.models import ReliabilityLevel
from quant_engine.risk.models import RiskLevel


class DecisionState(str, Enum):
    HOLD = "HOLD"
    REVIEW = "REVIEW"
    ADAPT = "ADAPT"


class ControlOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    regulated_signal: RegulatedSignal
    volatility_state: float = Field(ge=0.0)
    regime: MarketRegime
    risk_state: RiskLevel
    reliability_state: ReliabilityLevel
    control_output: float = Field(ge=-1.0, le=1.0)
    direction: SignalDirection
    decision_state: DecisionState
    reason_codes: list[str]
