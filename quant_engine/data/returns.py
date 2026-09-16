"""Lookahead-safe return construction from normalized market bars."""

import numpy as np
import pandas as pd

from quant_engine.data.models import MarketBar
from quant_engine.data.validation import normalize_market_data


def calculate_log_returns(bars: list[MarketBar]) -> pd.Series:
    """Return decimal close-to-close log returns without filling missing dates."""

    normalized = normalize_market_data(bars)
    if normalized.empty:
        return pd.Series(dtype=float, index=pd.DatetimeIndex([]), name="return")
    returns = np.log(normalized["close"] / normalized["close"].shift(1))
    returns.name = "return"
    return returns
