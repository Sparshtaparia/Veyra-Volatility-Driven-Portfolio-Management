"""API contracts for Phase 4 controlled signals."""

from datetime import date
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from quant_engine.risk.models import RiskState
from quant_engine.signals.models import ControlledSignal, ExplainabilityPayload


class SignalEvaluationRequest(BaseModel):
    as_of_date: date
    evaluation_id: UUID | None = None


class SignalEvaluationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    evaluation_id: UUID
    portfolio_id: str
    as_of_date: date
    risk_state: RiskState
    controlled_signals: list[ControlledSignal]


class ExplainabilityResponse(BaseModel):
    evaluation_id: UUID
    items: list[ExplainabilityPayload]
