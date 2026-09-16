"""
quant_engine/features/models.py
===============================
Domain contracts for feature snapshots.
"""

from datetime import date
from typing import Optional
from pydantic import BaseModel


class FeatureSnapshot(BaseModel):
    """
    A typed snapshot of all Phase 2 features for a given ticker and date.
    All features are calculated without lookahead bias.
    """
    ticker: str
    timestamp: date
    frequency: str = "DAILY"
    
    rsi: Optional[float] = None
    atr: Optional[float] = None
    macd_histogram: Optional[float] = None
    bollinger_band_width: Optional[float] = None
    dollar_volume: Optional[float] = None
