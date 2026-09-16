"""Operational API response contracts."""

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel


class RecentRunResponse(BaseModel):
    run_id: UUID
    run_type: str
    portfolio_id: str
    evaluation_date: date
    evaluation_id: UUID | None
    status: str
    provider: str
    started_at: datetime
    completed_at: datetime | None
    duration_ms: float | None
    error_type: str | None


class SystemStatusResponse(BaseModel):
    environment: str
    database: dict[str, str]
    scheduler: dict[str, object]
    market_data: dict[str, object]
    scheduled_run_counts: dict[str, int]
    recent_runs: list[RecentRunResponse]
    metrics: dict[str, object]
