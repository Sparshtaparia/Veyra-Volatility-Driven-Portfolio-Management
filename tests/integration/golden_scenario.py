"""Deterministic market scenario used by the documented golden-path demo."""

from __future__ import annotations

from datetime import date, timedelta
from math import exp, sin

from quant_engine.data.models import MarketBar
from quant_engine.data.provider import MarketDataProvider

TICKERS = ("AAA", "BBB", "CCC")
FIRST_EVALUATION_DATE = date(2025, 9, 10)
SECOND_EVALUATION_DATE = FIRST_EVALUATION_DATE + timedelta(days=1)


class GoldenMarketProvider(MarketDataProvider):
    """Purely deterministic OHLCV data; no random generator or network access."""

    def __init__(self) -> None:
        start = date(2024, 1, 1)
        bars: list[MarketBar] = []
        for ticker_index, ticker in enumerate(TICKERS):
            price = 100.0 + ticker_index * 12.0
            for offset in range((SECOND_EVALUATION_DATE - start).days + 1):
                timestamp = start + timedelta(days=offset)
                daily_return = (
                    0.00025
                    + 0.0045 * sin((offset + ticker_index * 5) / (7.0 + ticker_index))
                    + 0.0015 * sin((offset + ticker_index * 11) / 29.0)
                )
                price *= exp(daily_return)
                bars.append(
                    MarketBar(
                        ticker=ticker,
                        timestamp=timestamp,
                        open=price * 0.998,
                        high=price * 1.008,
                        low=price * 0.992,
                        close=price,
                        volume=1_000_000.0 + ticker_index * 100_000.0 + offset * 100.0,
                    )
                )
        self._bars = bars

    def get_history(self, ticker: str, start_date: date, end_date: date) -> list[MarketBar]:
        return [
            bar
            for bar in self._bars
            if bar.ticker == ticker and start_date <= bar.timestamp <= end_date
        ]

    def close(self, ticker: str, as_of_date: date) -> float:
        return self.get_latest_price(ticker, as_of_date)


def demo_holdings(provider: GoldenMarketProvider) -> list[dict[str, float | str]]:
    """Deliberately concentrated positions that deterministically require rebalancing."""

    quantities = {"AAA": 80.0, "BBB": 10.0, "CCC": 10.0}
    return [
        {
            "ticker": ticker,
            "quantity": quantities[ticker],
            "average_price": provider.close(ticker, FIRST_EVALUATION_DATE) * 0.95,
            "current_price": provider.close(ticker, FIRST_EVALUATION_DATE),
        }
        for ticker in TICKERS
    ]
