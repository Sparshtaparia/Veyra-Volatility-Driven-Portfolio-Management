"""
quant_engine/features/technical.py
==================================
Technical feature engineering.
No lookahead allowed.
"""

import numpy as np
import pandas as pd


def calculate_rsi(close_series: pd.Series, length: int = 14) -> pd.Series:
    """
    Calculate Relative Strength Index (RSI).
    """
    delta = close_series.diff()
    gain = (delta.where(delta > 0, 0)).fillna(0)
    loss = (-delta.where(delta < 0, 0)).fillna(0)

    # Use Wilder's smoothing (exponential with alpha = 1/length)
    # The first value should be the simple moving average
    avg_gain = gain.ewm(alpha=1 / length, adjust=False, min_periods=length).mean()
    avg_loss = loss.ewm(alpha=1 / length, adjust=False, min_periods=length).mean()

    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))

    # Handle edge case where loss is 0 (RSI = 100)
    rsi = rsi.fillna(100).where(avg_loss != 0, 100)
    return rsi


def calculate_atr(high: pd.Series, low: pd.Series, close: pd.Series, length: int = 14) -> pd.Series:
    """
    Calculate Average True Range (ATR).
    Raw ATR is returned to avoid the lookahead bias introduced by the full-sample
    Z-score normalization present in the research notebook.
    """
    prev_close = close.shift(1)

    tr1 = high - low
    tr2 = (high - prev_close).abs()
    tr3 = (low - prev_close).abs()

    true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

    # ATR is typically a Wilder's moving average of TR
    atr = true_range.ewm(alpha=1 / length, adjust=False, min_periods=length).mean()
    return atr


def calculate_macd_histogram(
    close: pd.Series, fast: int = 12, slow: int = 26, signal_len: int = 9
) -> pd.Series:
    """
    Calculate MACD Histogram.
    Raw histogram is returned to avoid lookahead bias.
    """
    ema_fast = close.ewm(span=fast, adjust=False).mean()
    ema_slow = close.ewm(span=slow, adjust=False).mean()

    macd = ema_fast - ema_slow
    signal = macd.ewm(span=signal_len, adjust=False).mean()

    histogram = macd - signal
    # Require at least 'slow' periods before emitting valid MACD
    histogram[: slow - 1] = np.nan
    return histogram


def calculate_bollinger_band_width(
    close: pd.Series, length: int = 20, num_std: float = 2.0
) -> pd.Series:
    """
    Calculate Bollinger Band Width.
    Definition: (Upper - Lower) / Middle
    """
    middle = close.rolling(window=length, min_periods=length).mean()
    std = close.rolling(window=length, min_periods=length).std()

    upper = middle + (std * num_std)
    lower = middle - (std * num_std)

    # Avoid division by zero
    bandwidth = np.where(middle != 0, (upper - lower) / middle, np.nan)
    return pd.Series(bandwidth, index=close.index)
