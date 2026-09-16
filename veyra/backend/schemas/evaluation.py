"""
backend/schemas/evaluation.py
=============================
FastAPI schemas for Evaluation API.
"""

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel

from quant_engine.domain import EvaluationDecision, EvaluationStatus, EvaluationTrigger

class EvaluatePortfolioRequest(BaseModel):
    evaluation_date: date
    trigger: EvaluationTrigger

class EvaluationResponse(BaseModel):
    evaluation_id: UUID
    portfolio_id: str
    evaluation_date: date
    trigger: EvaluationTrigger
    decision: EvaluationDecision
    status: EvaluationStatus
    created_at: datetime
