"""Backtest, metric, attribution, and ablation contracts."""

from datetime import date
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class BacktestModel(BaseModel):
    model_config = ConfigDict(allow_inf_nan=False, extra="forbid")


class AblationVariant(str, Enum):
    BASE_MULTI_FACTOR = "BASE_MULTI_FACTOR"
    NO_GARCH = "NO_GARCH"
    GARCH_SIZING_ONLY = "GARCH_SIZING_ONLY"
    NO_REGIME_CONTROL = "NO_REGIME_CONTROL"
    NO_RELIABILITY = "NO_RELIABILITY"
    NO_RISK_COUPLING = "NO_RISK_COUPLING"
    FULL_STATE_COUPLED = "FULL_STATE_COUPLED"


class BacktestConfig(BacktestModel):
    transaction_cost_bps: float = Field(default=5.0, ge=0.0)
    slippage_bps: float = Field(default=2.0, ge=0.0)
    annualization_factor: int = Field(default=252, gt=1)
    rebalance_frequency: str = "MONTHLY"


class BacktestReturn(BacktestModel):
    signal_date: date
    rebalance_date: date
    execution_date: date
    return_realization_date: date
    gross_return: float
    net_return: float
    benchmark_return: float
    turnover: float = Field(ge=0.0)
    transaction_cost: float = Field(ge=0.0)


class BacktestMetrics(BacktestModel):
    total_return: float
    cagr: float
    sharpe: float
    sortino: float
    calmar: float
    max_drawdown: float = Field(ge=0.0)
    volatility: float = Field(ge=0.0)
    win_rate: float = Field(ge=0.0, le=1.0)
    turnover: float = Field(ge=0.0)
    alpha: float
    beta: float


class AttributionItem(BacktestModel):
    ticker: str
    cumulative_contribution: float


class BacktestResult(BacktestModel):
    name: str
    start_date: date
    end_date: date
    returns: list[BacktestReturn]
    metrics: BacktestMetrics
    attribution: list[AttributionItem]


class PipelineBacktestConfig(BacktestModel):
    start_date: date
    end_date: date
    universe: list[str]
    transaction_cost_bps: float = Field(default=5.0, ge=0.0)
    slippage_bps: float = Field(default=2.0, ge=0.0)
    rebalance_threshold: float = Field(default=0.05, ge=0.0)
    feedback_eta: float = Field(default=0.1, ge=0.0)


class PipelineEvaluationRecord(BacktestModel):
    evaluation_date: date
    portfolio_value: float
    gross_return: float
    net_return: float
    benchmark_return: float
    turnover: float
    transaction_cost: float
    adaptive_threshold: float
    rebalance_executed: bool


class PipelineBacktestResult(BacktestModel):
    name: str
    config: PipelineBacktestConfig
    records: list[PipelineEvaluationRecord]
    metrics: BacktestMetrics
    benchmark_metrics: BacktestMetrics
    evaluations_count: int
    rebalances_count: int
