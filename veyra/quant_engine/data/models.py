"""
quant_engine/data/models.py
===========================
Domain contracts for market data.
"""

from datetime import date
from pydantic import BaseModel, field_validator, model_validator


class MarketBar(BaseModel):
    """
    A single bar of normalized OHLCV data.
    """
    ticker: str
    timestamp: date
    open: float
    high: float
    low: float
    close: float
    volume: float

    @field_validator("ticker")
    @classmethod
    def normalize_ticker(cls, v: str) -> str:
        stripped = v.strip()
        if not stripped:
            raise ValueError("ticker must not be empty")
        return stripped.upper()

    @field_validator("open", "high", "low", "close")
    @classmethod
    def validate_price_positive(cls, v: float, info) -> float:
        if v <= 0:
            raise ValueError(f"Price {info.field_name} must be > 0, got {v}")
        return v

    @field_validator("volume")
    @classmethod
    def validate_volume_non_negative(cls, v: float) -> float:
        if v < 0:
            raise ValueError(f"Volume must be >= 0, got {v}")
        return v

    @model_validator(mode="after")
    def validate_ohlc_relationships(self) -> "MarketBar":
        if self.high < self.low:
            raise ValueError(f"high ({self.high}) cannot be < low ({self.low})")
        if self.high < self.open or self.high < self.close:
            raise ValueError(f"high must be >= open and close")
        if self.low > self.open or self.low > self.close:
            raise ValueError(f"low must be <= open and close")
        return self
