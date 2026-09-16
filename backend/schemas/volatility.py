"""FastAPI schemas for persisted volatility and regime evaluations."""

from datetime import date
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from quant_engine.volatility.models import GARCHFitStatus, MarketRegime


class VolatilityEvaluationRequest(BaseModel):
    as_of_date: date
    evaluation_id: UUID | None = None


class AssetVolatilityResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    ticker: str
    conditional_volatility: float
    forecast_volatility: float
    realized_volatility: float
    volatility_ratio: float
    fit_status: GARCHFitStatus
    used_fallback: bool


class MarketRegimeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    as_of_date: date
    stress_score: float
    adaptive_threshold: float
    regime: MarketRegime
    eligible_asset_count: int
    coverage_ratio: float
    distance_to_threshold: float


class VolatilityEvaluationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    evaluation_id: UUID
    portfolio_id: str
    as_of_date: date
    market_regime: MarketRegimeResponse
    asset_volatility: list[AssetVolatilityResponse]
