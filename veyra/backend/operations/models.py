"""Typed contracts for scheduled operations."""

from datetime import date
from enum import Enum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class RunType(str, Enum):
    FULL_EVALUATION = "FULL_EVALUATION"
    VOLATILITY_REFRESH = "VOLATILITY_REFRESH"


class RunStatus(str, Enum):
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class ScheduledRunResult(BaseModel):
    model_config = ConfigDict(allow_inf_nan=False, extra="forbid")

    run_id: UUID
    run_type: RunType
    portfolio_id: str
    evaluation_date: date
    evaluation_id: UUID | None
    status: RunStatus
    claimed: bool
    duration_ms: float | None = Field(default=None, ge=0.0)
    stage_timings: dict[str, float] = Field(default_factory=dict)
    error_type: str | None = None
