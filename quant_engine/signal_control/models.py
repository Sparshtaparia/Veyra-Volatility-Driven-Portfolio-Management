"""Volatility-conditioned signal attenuation contracts."""
from pydantic import BaseModel, ConfigDict, Field

from quant_engine.signals.models import BaseSignal, SignalDirection
from quant_engine.volatility.models import MarketRegime


class RegulatedSignal(BaseModel):
    model_config = ConfigDict(extra="forbid")
    base_signal: BaseSignal
    regime: MarketRegime
    volatility_ratio: float = Field(ge=0.0)
    attenuation_factor: float = Field(gt=0.0, le=1.0)
    regulated_signal: float = Field(ge=-1.0, le=1.0)
    direction: SignalDirection
