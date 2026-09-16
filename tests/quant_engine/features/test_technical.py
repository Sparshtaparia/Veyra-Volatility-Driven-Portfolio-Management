"""
tests/quant_engine/features/test_technical.py
=============================================
Tests for technical features logic.
"""

import numpy as np
import pandas as pd

from quant_engine.features.liquidity import calculate_dollar_volume
from quant_engine.features.technical import (
    calculate_atr,
    calculate_bollinger_band_width,
    calculate_macd_histogram,
    calculate_rsi,
)


def test_calculate_rsi():
    close = pd.Series(
        [100, 102, 104, 103, 105, 106, 108, 107, 109, 110, 111, 112, 110, 109, 108, 107]
    )
    rsi = calculate_rsi(close, length=14)
    assert len(rsi) == 16
    assert not np.isnan(rsi.iloc[-1])
    assert 0 <= rsi.iloc[-1] <= 100


def test_calculate_atr():
    high = pd.Series([105, 106, 107])
    low = pd.Series([95, 96, 97])
    close = pd.Series([100, 101, 102])

    atr = calculate_atr(high, low, close, length=2)
    assert len(atr) == 3
    # True range for day 2: max(106-96, |106-100|, |96-100|) = 10
    # True range for day 3: max(107-97, |107-101|, |97-101|) = 10
    assert not np.isnan(atr.iloc[-1])


def test_calculate_macd_histogram():
    close = pd.Series(np.linspace(100, 150, 50))
    macd_hist = calculate_macd_histogram(close, fast=12, slow=26, signal_len=9)
    assert len(macd_hist) == 50
    # First 25 should be NaN
    assert np.isnan(macd_hist.iloc[24])
    assert not np.isnan(macd_hist.iloc[25])


def test_calculate_bollinger_band_width():
    close = pd.Series(np.linspace(100, 150, 30))
    bb = calculate_bollinger_band_width(close, length=20, num_std=2.0)
    assert len(bb) == 30
    assert np.isnan(bb.iloc[18])
    assert not np.isnan(bb.iloc[19])
    assert bb.iloc[-1] > 0


def test_calculate_dollar_volume():
    close = pd.Series([10, 20, 30])
    volume = pd.Series([100, 200, 300])
    dv = calculate_dollar_volume(close, volume)
    assert dv.iloc[0] == 1000
    assert dv.iloc[1] == 4000
    assert dv.iloc[2] == 9000
