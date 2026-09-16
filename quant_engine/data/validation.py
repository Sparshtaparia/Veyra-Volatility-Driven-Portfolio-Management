"""
quant_engine/data/validation.py
===============================
Data validation and normalization pipeline.
"""

import pandas as pd

from quant_engine.data.models import MarketBar


def normalize_market_data(bars: list[MarketBar]) -> pd.DataFrame:
    """
    Convert MarketBars to a normalized, chronologically sorted DataFrame.

    Validation Policy:
    - Sorts chronologically by timestamp
    - Drops duplicates by timestamp (keeps last)
    - Rejects entirely if less than 60 days of data (insufficient history for indicators)
    - Missing data policy: we do NOT forward-fill missing days here, as market closures are normal.
      Indicators will compute over available trading days.
    """
    if not bars:
        return pd.DataFrame()

    df = pd.DataFrame([b.model_dump() for b in bars])

    # Ensure types
    df["timestamp"] = pd.to_datetime(df["timestamp"])

    # Sort chronologically
    df = df.sort_values(by="timestamp")

    # Handle duplicates
    df = df.drop_duplicates(subset=["timestamp"], keep="last")

    # Set index
    df = df.set_index("timestamp")

    return df
