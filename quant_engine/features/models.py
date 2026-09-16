"""
quant_engine/features/models.py
===============================
Domain contracts for feature snapshots.
"""

from datetime import date

from pydantic import BaseModel


class FeatureSnapshot(BaseModel):
    """
    A typed snapshot of all Phase 2 features for a given ticker and date.
    All features are calculated without lookahead bias.
    """

    ticker: str
    timestamp: date
    frequency: str = "DAILY"

    rsi: float | None = None
    atr: float | None = None
    macd_histogram: float | None = None
    bollinger_band_width: float | None = None
    dollar_volume: float | None = None
