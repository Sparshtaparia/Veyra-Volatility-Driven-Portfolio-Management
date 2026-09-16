"""
quant_engine/features/service.py
================================
Service to orchestrate feature calculation.
"""

from datetime import date

import numpy as np

from quant_engine.data.provider import MarketDataProvider
from quant_engine.data.validation import normalize_market_data
from quant_engine.features.liquidity import calculate_dollar_volume
from quant_engine.features.models import FeatureSnapshot
from quant_engine.features.technical import (
    calculate_atr,
    calculate_bollinger_band_width,
    calculate_macd_histogram,
    calculate_rsi,
)


class FeatureService:
    def __init__(self, provider: MarketDataProvider):
        self.provider = provider

    def generate_features(
        self, ticker: str, start_date: date, end_date: date
    ) -> list[FeatureSnapshot]:
        """
        Fetch raw market data, validate, and compute technical/liquidity features.
        Returns a chronologically ordered list of FeatureSnapshots.
        """
        raw_bars = self.provider.get_history(ticker, start_date, end_date)

        df = normalize_market_data(raw_bars)
        if df.empty or len(df) < 60:
            # Not enough data to compute indicators like MACD safely
            return []

        # Add ticker column back if missing, though it should be in the DataFrame
        if "ticker" not in df.columns:
            df["ticker"] = ticker

        close = df["close"]
        high = df["high"]
        low = df["low"]
        volume = df["volume"]

        # Calculate features
        rsi = calculate_rsi(close)
        atr = calculate_atr(high, low, close)
        macd_hist = calculate_macd_histogram(close)
        bb_width = calculate_bollinger_band_width(close)
        dollar_vol = calculate_dollar_volume(close, volume)

        # Build snapshots
        snapshots = []
        for dt, row in df.iterrows():
            timestamp = dt.date()

            # Use np.isnan to safely handle NaNs before placing in model, replacing with None
            val_rsi = rsi.loc[dt] if not np.isnan(rsi.loc[dt]) else None
            val_atr = atr.loc[dt] if not np.isnan(atr.loc[dt]) else None
            val_macd = macd_hist.loc[dt] if not np.isnan(macd_hist.loc[dt]) else None
            val_bb = bb_width.loc[dt] if not np.isnan(bb_width.loc[dt]) else None
            val_dv = dollar_vol.loc[dt] if not np.isnan(dollar_vol.loc[dt]) else None

            snap = FeatureSnapshot(
                ticker=row["ticker"],
                timestamp=timestamp,
                frequency="DAILY",
                rsi=val_rsi,
                atr=val_atr,
                macd_histogram=val_macd,
                bollinger_band_width=val_bb,
                dollar_volume=val_dv,
            )
            snapshots.append(snap)

        return snapshots
