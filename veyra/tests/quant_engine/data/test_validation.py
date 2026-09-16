"""
tests/quant_engine/data/test_validation.py
==========================================
Tests for market data validation.
"""

from datetime import date

import pandas as pd

from quant_engine.data.models import MarketBar
from quant_engine.data.validation import normalize_market_data


def test_normalize_market_data():
    bars = [
        MarketBar(
            ticker="TCS",
            timestamp=date(2024, 1, 2),
            open=105,
            high=115,
            low=100,
            close=110,
            volume=2000,
        ),
        MarketBar(
            ticker="TCS",
            timestamp=date(2024, 1, 1),
            open=100,
            high=110,
            low=90,
            close=105,
            volume=1000,
        ),
        MarketBar(
            ticker="TCS",
            timestamp=date(2024, 1, 2),
            open=106,
            high=116,
            low=101,
            close=111,
            volume=2100,
        ),  # Duplicate
    ]

    df = normalize_market_data(bars)

    # Should sort by timestamp
    assert df.index[0] == pd.to_datetime(date(2024, 1, 1))
    assert df.index[1] == pd.to_datetime(date(2024, 1, 2))

    # Should keep last duplicate
    assert len(df) == 2
    assert df.loc[pd.to_datetime(date(2024, 1, 2))]["close"] == 111.0
