"""API contracts for Analytics Dashboard."""

from datetime import date, datetime
from pydantic import BaseModel, ConfigDict
from typing import Literal

class PerformanceStats(BaseModel):
    portfolio_value: float
    invested_amount: float
    absolute_return: float
    return_percentage: float | None

class RiskScoreComponent(BaseModel):
    score: int
    label: str

class RiskAssessment(BaseModel):
    overall_score: int | None
    label: str
    components: dict[str, RiskScoreComponent]
    explanations: list[str]

class ConcentrationMetrics(BaseModel):
    largest_position: float | None
    top_3: float | None
    hhi: float | None
    
class SnapshotDataPoint(BaseModel):
    date: str
    portfolio_value: float

class RecentDecision(BaseModel):
    date: str
    action: str
    asset: str
    weight_change: float
    reason: str

class AdaptiveThresholdState(BaseModel):
    previous: float
    observed: float
    updated: float
    change: float

class DataStats(BaseModel):
    portfolio_valuations: int
    holdings: int
    transactions: int
    rebalance_evaluations: int
    history_days: int
    last_updated: datetime | None

class AnalyticsDashboardResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    portfolio_id: str
    performance: PerformanceStats
    risk_assessment: RiskAssessment | None
    concentration: ConcentrationMetrics
    volatility: float | None
    max_drawdown: float | None
    performance_history: list[SnapshotDataPoint]
    recent_decisions: list[RecentDecision]
    adaptive_threshold: AdaptiveThresholdState | None
    data_stats: DataStats
