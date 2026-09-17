"""API contracts for Phase 4 decision-level outputs."""
from datetime import date
from uuid import UUID

from pydantic import BaseModel

from quant_engine.control.models import DecisionState
from quant_engine.optimization.models import AllocationResult
from quant_engine.reliability.models import ReliabilityLevel
from quant_engine.risk.models import RiskLevel
from quant_engine.signals.models import SignalDirection
from quant_engine.volatility.models import MarketRegime


class SignalDecisionEvaluationRequest(BaseModel):
    as_of_date: date
    evaluation_id: UUID | None = None


class AssetDecisionResponse(BaseModel):
    ticker: str
    base_signal: float
    regulated_signal: float
    attenuation_factor: float
    control_output: float
    direction: SignalDirection
    decision_state: DecisionState
    regime: MarketRegime
    volatility_state: float
    risk_state: RiskLevel
    reliability_state: ReliabilityLevel
    reason_codes: list[str]

class SignalDecisionEvaluationResponse(BaseModel):
    evaluation_id: UUID
    portfolio_id: str
    as_of_date: date
    controls: list[AssetDecisionResponse]
    composite_risk: dict
    allocation_result: AllocationResult | None = None
