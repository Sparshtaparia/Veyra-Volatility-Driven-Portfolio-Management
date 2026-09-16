"""
quant_engine/features/liquidity.py
==================================
Liquidity feature engineering.
"""

import pandas as pd


def calculate_dollar_volume(close: pd.Series, volume: pd.Series) -> pd.Series:
    """
    Calculate Dollar Volume.
    Definition: Close * Volume

    This is a proxy for liquidity/trading activity, NOT a prediction signal.
    """
    return close * volume
