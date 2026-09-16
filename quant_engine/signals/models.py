
"""Typed, deterministic Phase 4 base-signal contracts."""
from datetime import date
from enum import Enum
from pydantic import BaseModel, ConfigDict, Field, field_validator


class SignalDirection(str, Enum):
    BUY = "BUY"
    SELL = "SELL"
    NEUTRAL = "NEUTRAL"


class SignalComponents(BaseModel):
    model_config = ConfigDict(extra="forbid")
    rsi: float = Field(ge=-1.0, le=1.0)
    macd_momentum: float = Field(ge=-1.0, le=1.0)
    band_width_penalty: float = Field(ge=0.0, le=1.0)


class BaseSignal(BaseModel):
    model_config = ConfigDict(extra="forbid")
    ticker: str
    timestamp: date
    components: SignalComponents
    composite_signal: float = Field(ge=-1.0, le=1.0)
    direction: SignalDirection

    @field_validator("ticker")
    @classmethod
    def normalize_ticker(cls, value: str) -> str:
        value = value.strip().upper()
        if not value:
            raise ValueError("ticker must not be empty")
        return value

