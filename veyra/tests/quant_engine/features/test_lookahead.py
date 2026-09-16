"""
tests/quant_engine/features/test_lookahead.py
=============================================
Critical lookahead bias tests for features.
"""

import numpy as np
import pandas as pd

from quant_engine.features.technical import (
    calculate_atr,
    calculate_macd_histogram,
)


def test_no_lookahead_atr():
    # Base case
    high = pd.Series(np.linspace(100, 150, 50))
    low = pd.Series(np.linspace(90, 140, 50))
    close = pd.Series(np.linspace(95, 145, 50))

    atr_base = calculate_atr(high, low, close)

    # Mutate a future value (t=40)
    high_mutated = high.copy()
    high_mutated.iloc[40] = 500  # Massive spike

    atr_mutated = calculate_atr(high_mutated, low, close)

    # Values BEFORE the mutation (t=0 to 39) MUST be identical
    pd.testing.assert_series_equal(atr_base.iloc[:40], atr_mutated.iloc[:40])

    # Values at and after the mutation will be different
    assert atr_base.iloc[40] != atr_mutated.iloc[40]


def test_no_lookahead_macd():
    close = pd.Series(np.linspace(100, 150, 50))
    macd_base = calculate_macd_histogram(close)

    close_mutated = close.copy()
    close_mutated.iloc[40] = 500

    macd_mutated = calculate_macd_histogram(close_mutated)

    pd.testing.assert_series_equal(macd_base.iloc[25:40], macd_mutated.iloc[25:40])
    assert macd_base.iloc[40] != macd_mutated.iloc[40]
