"""Typed contracts for Phase 4 factor intelligence."""

from __future__ import annotations

from datetime import date
from enum import Enum
from math import isfinite

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class FactorModel(BaseModel):
    model_config = ConfigDict(allow_inf_nan=False, extra="forbid")


class NormalizationMethod(str, Enum):
    Z_SCORE = "Z_SCORE"
    PERCENTILE_RANK = "PERCENTILE_RANK"


class FamaFrenchExposure(FactorModel):
    ticker: str
    as_of_date: date
    alpha: float
    market_beta: float
    smb_beta: float
    hml_beta: float
    rmw_beta: float
    cma_beta: float
    r_squared: float = Field(ge=0.0, le=1.0)
    observation_count: int = Field(gt=0)

    @field_validator("ticker")
    @classmethod
    def normalize_ticker(cls, value: str) -> str:
        value = value.strip().upper()
        if not value:
            raise ValueError("ticker must not be empty")
        return value


class FactorSnapshot(FactorModel):
    ticker: str
    as_of_date: date
    raw_factors: dict[str, float]
    normalized_factors: dict[str, float]
    normalization_method: NormalizationMethod

    @field_validator("ticker")
    @classmethod
    def normalize_ticker(cls, value: str) -> str:
        value = value.strip().upper()
        if not value:
            raise ValueError("ticker must not be empty")
        return value

    @model_validator(mode="after")
    def validate_factor_keys(self) -> FactorSnapshot:
        if not self.raw_factors:
            raise ValueError("raw_factors must not be empty")
        if set(self.raw_factors) != set(self.normalized_factors):
            raise ValueError("raw and normalized factor keys must match")
        return self


DEFAULT_FACTOR_WEIGHTS = {
    "rsi": -0.10,
    "atr": -0.10,
    "macd_histogram": 0.15,
    "bollinger_band_width": -0.10,
    "dollar_volume": 0.10,
    "ff_alpha": 0.25,
    "smb_beta": 0.05,
    "hml_beta": 0.05,
    "rmw_beta": 0.05,
    "cma_beta": 0.05,
}


class SignalConfig(FactorModel):
    weights: dict[str, float] = Field(default_factory=lambda: DEFAULT_FACTOR_WEIGHTS.copy())

    @field_validator("weights")
    @classmethod
    def validate_weights(cls, weights: dict[str, float]) -> dict[str, float]:
        if not weights or any(not isfinite(value) for value in weights.values()):
            raise ValueError("factor weights must be non-empty and finite")
        return weights


class BaseSignal(FactorModel):
    ticker: str
    as_of_date: date
    base_signal: float
    contributions: dict[str, float]

    @model_validator(mode="after")
    def validate_contributions(self) -> BaseSignal:
        if abs(sum(self.contributions.values()) - self.base_signal) > 1e-10:
            raise ValueError("base_signal must equal the sum of factor contributions")
        return self
