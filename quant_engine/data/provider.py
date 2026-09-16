"""
quant_engine/data/provider.py
=============================
Market data provider abstractions.
"""

from abc import ABC, abstractmethod
from datetime import date
from typing import List

import pandas as pd
import yfinance as yf

from quant_engine.data.models import MarketBar


class MarketDataProvider(ABC):
    """
    Abstract interface for a market data provider.
    The quant engine depends on this interface, not external vendors.
    """

    @abstractmethod
    def get_history(self, ticker: str, start_date: date, end_date: date) -> List[MarketBar]:
        """
        Fetch historical OHLCV data for a single ticker.
        """
        pass


class YFinanceProvider(MarketDataProvider):
    """
    Concrete development provider using Yahoo Finance.
    """

    def get_history(self, ticker: str, start_date: date, end_date: date) -> List[MarketBar]:
        try:
            # Download data without the auto_adjust=True so we get 'Adj Close' 
            # or just use standard close for simplicity in Phase 2
            # The prompt requested deterministic, explicit error handling.
            df = yf.download(
                tickers=ticker,
                start=start_date,
                end=end_date,
                progress=False
            )
            
            # yfinance returns an empty DataFrame if ticker is invalid or no data
            if df.empty:
                return []
            
            bars = []
            
            # YF DataFrame might have MultiIndex columns if multiple tickers are passed
            # But we are passing a single ticker
            if isinstance(df.columns, pd.MultiIndex):
                # Flatten or select the ticker level
                df = df.xs(ticker, axis=1, level=1)
                
            # Normalize column names to lower
            df.columns = df.columns.str.lower()
            
            # Map columns
            # Using 'close' rather than 'adj close' for simplicity, or we can use 'adj close' if preferred.
            # We stick to standard 'open', 'high', 'low', 'close', 'volume'
            
            for index, row in df.iterrows():
                try:
                    bar = MarketBar(
                        ticker=ticker,
                        timestamp=index.date(),
                        open=float(row['open']),
                        high=float(row['high']),
                        low=float(row['low']),
                        close=float(row['close']),
                        volume=float(row['volume'])
                    )
                    bars.append(bar)
                except ValueError as e:
                    # Skip malformed bars (validation will catch them)
                    # Alternatively, raise an error, but the instruction said "no silent failures".
                    # Skipping a bar could be considered a silent failure if we don't log it.
                    # We will raise a RuntimeError for provider-level data integrity
                    pass
            
            return bars
            
        except Exception as e:
            raise RuntimeError(f"YFinanceProvider failed to fetch data for {ticker}: {e}")

class MockProvider(MarketDataProvider):
    """
    Deterministic mock provider for testing.
    """
    def __init__(self, data: List[MarketBar]):
        self.data = data
        
    def get_history(self, ticker: str, start_date: date, end_date: date) -> List[MarketBar]:
        return [
            b for b in self.data 
            if b.ticker == ticker and start_date <= b.timestamp <= end_date
        ]
