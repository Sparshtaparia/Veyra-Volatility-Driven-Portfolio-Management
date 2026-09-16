"""Typed Phase 5 portfolio construction contracts."""

from datetime import date
from enum import Enum
from math import isclose

from pydantic import BaseModel, ConfigDict, Field, model_validator

from quant_engine.volatility.models import MarketRegime


class PortfolioModel(BaseModel):
    model_config = ConfigDict(allow_inf_nan=False, extra="forbid")


class ExposureConfig(PortfolioModel):
    base_exposure: float = Field(default=1.0, gt=0.0, le=1.0)
    minimum_exposure: float = Field(default=0.2, ge=0.0, le=1.0)
    maximum_exposure: float = Field(default=1.0, gt=0.0, le=1.0)
    risk_sensitivity: float = Field(default=0.75, ge=0.0)
    regime_factors: dict[MarketRegime, float] = Field(
        default_factory=lambda: {
            MarketRegime.LOW_VOL: 1.0,
            MarketRegime.NORMAL: 1.0,
            MarketRegime.ELEVATED: 0.75,
            MarketRegime.HIGH_STRESS: 0.45,
        }
    )


class ExposureState(PortfolioModel):
    base_exposure: float
    regime_factor: float
    risk_factor: float
    target_gross_exposure: float = Field(ge=0.0, le=1.0)
    target_net_exposure: float = Field(ge=0.0, le=1.0)


class OptimizerConfig(PortfolioModel):
    max_stock_weight: float = Field(default=0.25, gt=0.0, le=1.0)
    max_sector_exposure: float = Field(default=0.40, gt=0.0, le=1.0)
    target_volatility: float = Field(default=0.15, gt=0.0)
    signal_strength: float = Field(default=0.20, ge=0.0)
    baseline_penalty: float = Field(default=1.0, gt=0.0)
    turnover_penalty: float = Field(default=0.10, ge=0.0)
    minimum_cash_weight: float = Field(default=0.0, ge=0.0, lt=1.0)


class AssetAllocationInput(PortfolioModel):
    ticker: str
    sector: str = "UNKNOWN"
    current_weight: float = Field(ge=0.0, le=1.0)
    controlled_signal: float
    conditional_volatility: float = Field(gt=0.0)


class TargetWeight(PortfolioModel):
    ticker: str
    sector: str
    current_weight: float
    inverse_volatility_weight: float = Field(ge=0.0, le=1.0)
    target_weight: float = Field(ge=0.0, le=1.0)
    weight_change: float


class OptimizationResult(PortfolioModel):
    as_of_date: date
    targets: list[TargetWeight]
    gross_exposure: float = Field(ge=0.0)
    net_exposure: float
    cash_weight: float = Field(ge=0.0, le=1.0)
    expected_volatility: float = Field(ge=0.0)
    expected_turnover: float = Field(ge=0.0)
    solver_status: str

    @model_validator(mode="after")
    def validate_weights(self) -> "OptimizationResult":
        if not isclose(self.gross_exposure + self.cash_weight, 1.0, abs_tol=1e-6):
            raise ValueError("gross exposure plus cash must equal 1")
        return self


class TradeSide(str, Enum):
    BUY = "BUY"
    SELL = "SELL"


class RebalanceInstruction(PortfolioModel):
    ticker: str
    current_weight: float
    target_weight: float
    delta_weight: float
    notional_change: float
    trade_quantity: float = Field(gt=0.0)
    side: TradeSide
    reference_price: float = Field(gt=0.0)


class ExecutedTrade(PortfolioModel):
    ticker: str
    side: TradeSide
    quantity: float = Field(gt=0.0)
    reference_price: float = Field(gt=0.0)
    execution_price: float = Field(gt=0.0)
    gross_notional: float = Field(gt=0.0)
    transaction_cost: float = Field(ge=0.0)
    slippage_cost: float = Field(ge=0.0)
    net_cash_change: float
