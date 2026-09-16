"""
quant_engine/data/provider.py
=============================
Market data provider abstractions.
"""

import json
from abc import ABC, abstractmethod
from datetime import UTC, date, datetime, time
from urllib.parse import quote
from urllib.request import Request, urlopen

import pandas as pd
import yfinance as yf

from quant_engine.data.models import MarketBar


class MarketDataProvider(ABC):
    """
    Abstract interface for a market data provider.
    The quant engine depends on this interface, not external vendors.
    """

    @abstractmethod
    def get_history(self, ticker: str, start_date: date, end_date: date) -> list[MarketBar]:
        """
        Fetch historical OHLCV data for a single ticker.
        """
        pass


class YFinanceProvider(MarketDataProvider):
    """
    Concrete development provider using Yahoo Finance.
    """

    def __init__(self, timeout_seconds: float = 15.0) -> None:
        if timeout_seconds <= 0.0:
            raise ValueError("timeout_seconds must be positive")
        self.timeout_seconds = timeout_seconds

    def get_history(self, ticker: str, start_date: date, end_date: date) -> list[MarketBar]:
        try:
            df = yf.download(
                tickers=ticker,
                start=start_date,
                end=end_date,
                progress=False,
                auto_adjust=False,
                threads=False,
                timeout=self.timeout_seconds,
            )
            if df.empty:
                return []
            if isinstance(df.columns, pd.MultiIndex):
                df = df.xs(ticker, axis=1, level=1)
            df.columns = df.columns.str.lower()
            bars = []
            for index, row in df.iterrows():
                try:
                    bars.append(
                        MarketBar(
                            ticker=ticker,
                            timestamp=index.date(),
                            open=float(row["open"]),
                            high=float(row["high"]),
                            low=float(row["low"]),
                            close=float(row["close"]),
                            volume=float(row["volume"]),
                        )
                    )
                except (KeyError, TypeError, ValueError) as exc:
                    raise RuntimeError(f"Malformed yfinance bar for {ticker} at {index}") from exc
            return bars
        except Exception as exc:
            raise RuntimeError(
                f"YFinanceProvider failed to fetch data for {ticker}: {exc}"
            ) from exc


class YahooChartProvider(MarketDataProvider):
    """Fallback adapter using Yahoo's chart JSON endpoint directly."""

    def __init__(self, timeout_seconds: float = 15.0) -> None:
        if timeout_seconds <= 0.0:
            raise ValueError("timeout_seconds must be positive")
        self.timeout_seconds = timeout_seconds

    def get_history(self, ticker: str, start_date: date, end_date: date) -> list[MarketBar]:
        period1 = int(datetime.combine(start_date, time.min, tzinfo=UTC).timestamp())
        period2 = int(datetime.combine(end_date, time.min, tzinfo=UTC).timestamp())
        url = (
            "https://query1.finance.yahoo.com/v8/finance/chart/"
            f"{quote(ticker)}?period1={period1}&period2={period2}"
            "&interval=1d&events=history"
        )
        request = Request(url, headers={"User-Agent": "Veyra/0.2 market-data"})
        with urlopen(request, timeout=self.timeout_seconds) as response:
            payload = json.loads(response.read())
        try:
            result = payload["chart"]["result"][0]
            timestamps = result.get("timestamp", [])
            quotes = result["indicators"]["quote"][0]
            bars = []
            for index, timestamp in enumerate(timestamps):
                values = {
                    name: quotes[name][index] for name in ("open", "high", "low", "close", "volume")
                }
                if any(value is None for value in values.values()):
                    continue
                bars.append(
                    MarketBar(
                        ticker=ticker,
                        timestamp=datetime.fromtimestamp(timestamp, tz=UTC).date(),
                        open=float(values["open"]),
                        high=float(values["high"]),
                        low=float(values["low"]),
                        close=float(values["close"]),
                        volume=float(values["volume"]),
                    )
                )
            return bars
        except (KeyError, IndexError, TypeError, ValueError) as exc:
            description = payload.get("chart", {}).get("error")
            raise RuntimeError(
                f"YahooChartProvider returned malformed data for {ticker}: {description}"
            ) from exc


class AlphaVantageProvider(MarketDataProvider):
    """Independent daily OHLCV adapter for Alpha Vantage.

    Alpha Vantage is intentionally optional: callers must provide an API key.
    Its data path is independent of Yahoo, making it suitable for a real
    fallback when Yahoo rate-limits both of the Yahoo-backed adapters.
    """

    def __init__(self, api_key: str, timeout_seconds: float = 15.0) -> None:
        if not api_key.strip():
            raise ValueError("Alpha Vantage API key must not be empty")
        if timeout_seconds <= 0.0:
            raise ValueError("timeout_seconds must be positive")
        self.api_key = api_key
        self.timeout_seconds = timeout_seconds

    def get_history(self, ticker: str, start_date: date, end_date: date) -> list[MarketBar]:
        url = (
            "https://www.alphavantage.co/query?function=TIME_SERIES_DAILY"
            f"&symbol={quote(ticker)}&outputsize=full&apikey={quote(self.api_key)}"
        )
        request = Request(url, headers={"User-Agent": "Veyra/0.2 market-data"})
        with urlopen(request, timeout=self.timeout_seconds) as response:
            payload = json.loads(response.read())
        series = payload.get("Time Series (Daily)")
        if not isinstance(series, dict):
            message = (
                payload.get("Note") or payload.get("Information") or payload.get("Error Message")
            )
            raise RuntimeError(
                f"AlphaVantageProvider returned no daily data for {ticker}: {message}"
            )
        bars = []
        try:
            for timestamp_text, values in series.items():
                timestamp = date.fromisoformat(timestamp_text)
                if not start_date <= timestamp <= end_date:
                    continue
                bars.append(
                    MarketBar(
                        ticker=ticker,
                        timestamp=timestamp,
                        open=float(values["1. open"]),
                        high=float(values["2. high"]),
                        low=float(values["3. low"]),
                        close=float(values["4. close"]),
                        volume=float(values["5. volume"]),
                    )
                )
        except (KeyError, TypeError, ValueError) as exc:
            raise RuntimeError(f"Malformed Alpha Vantage bar for {ticker}") from exc
        return sorted(bars, key=lambda item: item.timestamp)


class MockProvider(MarketDataProvider):
    """
    Deterministic mock provider for testing.
    """

    def __init__(self, data: list[MarketBar]):
        self.data = data

    def get_history(self, ticker: str, start_date: date, end_date: date) -> list[MarketBar]:
        return [
            b for b in self.data if b.ticker == ticker and start_date <= b.timestamp <= end_date
        ]
