"""Contracts for X(t+1) = F(X(t), u(t), Y(t+1))."""

from datetime import date

from pydantic import BaseModel, ConfigDict, Field


class FeedbackModel(BaseModel):
    model_config = ConfigDict(allow_inf_nan=False, extra="forbid")


class FeedbackConfig(FeedbackModel):
    learning_rate: float = Field(default=0.10, gt=0.0, le=1.0)
    minimum_reliability_multiplier: float = Field(default=0.25, gt=0.0, le=1.0)
    minimum_exposure_limit: float = Field(default=0.20, gt=0.0, le=1.0)
    maximum_exposure_limit: float = Field(default=1.0, gt=0.0, le=1.0)


class SystemState(FeedbackModel):
    as_of_date: date
    volatility_distribution_level: float = Field(gt=0.0)
    adaptive_threshold: float = Field(gt=0.0)
    reliability_multiplier: float = Field(gt=0.0, le=1.0)
    risk_limit: float = Field(gt=0.0, le=1.0)
    exposure_limit: float = Field(gt=0.0, le=1.0)
    portfolio_value: float = Field(ge=0.0)


class FeedbackOutcome(FeedbackModel):
    observation_date: date
    portfolio_return: float
    realized_volatility: float = Field(ge=0.0)
    drawdown: float = Field(ge=0.0, le=1.0)
    signal_accuracy: float = Field(ge=-1.0, le=1.0)
    transaction_cost: float = Field(ge=0.0)


class FeedbackUpdate(FeedbackModel):
    previous_state: SystemState
    controlled_signal: float
    outcome: FeedbackOutcome
    updated_state: SystemState
