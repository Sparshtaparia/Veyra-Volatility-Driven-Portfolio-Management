"""
Simple benchmarks for backtesting validation.
"""
from datetime import date
from typing import Sequence

import numpy as np
import pandas as pd

from quant_engine.data.provider import MarketDataProvider
from quant_engine.data.returns import calculate_log_returns


def compute_equal_weight_benchmark(
    provider: MarketDataProvider,
    universe: Sequence[str],
    start_date: date,
    end_date: date,
) -> pd.Series:
    """
    Computes a daily return series for an equal-weighted portfolio of the given universe.
    Rebalances daily to equal weight.
    """
    if not universe:
        raise ValueError("Universe cannot be empty")
        
    all_returns = {}
    for ticker in universe:
        bars = provider.get_history(ticker, start_date, end_date)
        ret = calculate_log_returns(bars)
        # Convert log returns back to simple returns for portfolio aggregation
        simple_ret = (np.exp(ret) - 1.0) if not ret.empty else pd.Series(dtype=float)
        all_returns[ticker] = simple_ret
        
    df = pd.DataFrame(all_returns)
    df = df.fillna(0.0)
    
    # Equal weight return is the mean of individual simple returns
    ew_return = df.mean(axis=1)
    return ew_return

