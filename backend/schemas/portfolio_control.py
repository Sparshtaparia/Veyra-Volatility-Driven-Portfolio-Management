"""API contracts for upload, optimization, paper execution, feedback, and backtests."""

from datetime import date
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from quant_engine.backtest.models import BacktestResult
from quant_engine.feedback.models import FeedbackOutcome
from quant_engine.portfolio.models import (
    ExecutedTrade,
    ExposureConfig,
    OptimizationResult,
    OptimizerConfig,
)


class ManualHoldingRequest(BaseModel):
    ticker: str
    quantity: float = Field(gt=0.0)
    average_price: float = Field(gt=0.0)


class ManualPortfolioRequest(BaseModel):
    name: str
    currency: str = "USD"
    as_of_date: date
    holdings: list[ManualHoldingRequest]


class UploadedHoldingResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    ticker: str
    quantity: float
    average_price: float
    current_price: float
    market_value: float
    weight: float


class PortfolioUploadResponse(BaseModel):
    portfolio_id: str
    name: str
    currency: str
    total_value: float
    holdings: list[UploadedHoldingResponse]


class PortfolioControlRequest(BaseModel):
    evaluation_id: UUID
    sectors: dict[str, str] = Field(default_factory=dict)
    exposure_config: ExposureConfig | None = None
    optimizer_config: OptimizerConfig | None = None
    transaction_cost_bps: float = Field(default=5.0, ge=0.0)
    slippage_bps: float = Field(default=2.0, ge=0.0)


class PortfolioControlResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    evaluation_id: UUID
    portfolio_id: str
    optimization: OptimizationResult
    trades: list[ExecutedTrade]
    rebalance_event_id: UUID


class FeedbackRequest(BaseModel):
    evaluation_id: UUID
    outcome: FeedbackOutcome


class FeedbackHistoryItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    evaluation_id: UUID
    portfolio_id: str
    observation_date: date
    previous_state: dict[str, object]
    controlled_signal: float
    observed_outcome: dict[str, object]
    updated_state: dict[str, object]


class BacktestDetailResponse(BaseModel):
    backtest_id: UUID
    portfolio_id: str | None
    name: str
    variant: str
    start_date: date
    end_date: date
    status: str
    configuration: dict[str, object]
    returns: list[dict[str, object]]
    metrics: dict[str, object]


class BacktestRunRequest(BaseModel):
    name: str
    portfolio_id: str | None = None
    return_dates: list[date]
    asset_returns: dict[str, list[float]]
    signal_dates: list[date]
    target_weights: dict[str, list[float]]
    benchmark_returns: list[float]


class BacktestRunResponse(BaseModel):
    backtest_id: UUID
    result: BacktestResult


class AblationRunRequest(BaseModel):
    portfolio_id: str | None = None
    return_dates: list[date]
    asset_returns: dict[str, list[float]]
    signal_dates: list[date]
    variant_weights: dict[str, dict[str, list[float]]]
    benchmark_returns: list[float]


class AblationItemResponse(BaseModel):
    backtest_id: UUID
    result: BacktestResult


class AblationRunResponse(BaseModel):
    variants: dict[str, AblationItemResponse]
