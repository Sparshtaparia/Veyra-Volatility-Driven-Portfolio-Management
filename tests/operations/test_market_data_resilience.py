"""Retry, fallback, caching, freshness, and date-boundary tests."""

from datetime import date
from time import sleep

import pytest

from backend.operations.market_data import (
    MarketDataOperationalError,
    ProviderPolicy,
    ResilientMarketDataProvider,
)
from quant_engine.data.models import MarketBar
from quant_engine.data.provider import MarketDataProvider


def bar(day: int, ticker: str = "AAA") -> MarketBar:
    return MarketBar(
        ticker=ticker,
        timestamp=date(2026, 1, day),
        open=100.0,
        high=101.0,
        low=99.0,
        close=100.0,
        volume=1_000.0,
    )


class SequenceProvider(MarketDataProvider):
    def __init__(self, outcomes) -> None:
        self.outcomes = list(outcomes)
        self.calls = 0

    def get_history(self, ticker: str, start_date: date, end_date: date):
        self.calls += 1
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


def policy(**updates) -> ProviderPolicy:
    values = {
        "attempts": 2,
        "base_backoff_seconds": 0.0,
        "max_backoff_seconds": 0.0,
        "timeout_seconds": 1.0,
        "requests_per_second": 100.0,
        "max_staleness_days": 2,
        "cache_ttl_seconds": 60,
    }
    values.update(updates)
    return ProviderPolicy(**values)


def test_retries_primary_then_uses_configured_fallback() -> None:
    primary = SequenceProvider([RuntimeError("temporary"), RuntimeError("still down")])
    fallback = SequenceProvider([[bar(9)]])
    provider = ResilientMarketDataProvider(
        primary,
        fallback=fallback,
        primary_name="primary",
        fallback_name="fallback",
        policy=policy(),
        sleep=lambda _seconds: None,
    )

    result = provider.get_history("aaa", date(2026, 1, 1), date(2026, 1, 10))

    assert result == [bar(9)]
    assert primary.calls == 2
    assert fallback.calls == 1
    assert provider.last_provider_for("AAA") == "fallback"
    provider.close()


def test_exhausts_primary_then_secondary_then_tertiary() -> None:
    primary = SequenceProvider([RuntimeError("primary unavailable")])
    secondary = SequenceProvider([RuntimeError("secondary unavailable")])
    tertiary = SequenceProvider([[bar(9)]])
    provider = ResilientMarketDataProvider(
        primary,
        fallback=secondary,
        tertiary=tertiary,
        primary_name="yfinance",
        fallback_name="alpha_vantage",
        tertiary_name="yahoo_chart",
        policy=policy(attempts=1),
        sleep=lambda _seconds: None,
    )

    assert provider.get_history("AAA", date(2026, 1, 1), date(2026, 1, 10)) == [bar(9)]
    assert (primary.calls, secondary.calls, tertiary.calls) == (1, 1, 1)
    assert provider.last_provider_for("AAA") == "yahoo_chart"
    assert provider.provider_provenance() == {"AAA": "yahoo_chart"}
    provider.close()


def test_stale_market_data_is_rejected() -> None:
    provider = ResilientMarketDataProvider(
        SequenceProvider([[bar(2)]]),
        policy=policy(attempts=1, max_staleness_days=2),
    )

    with pytest.raises(MarketDataOperationalError, match="market data unavailable"):
        provider.get_history("AAA", date(2026, 1, 1), date(2026, 1, 10))
    provider.close()


def test_cache_is_exact_request_scoped_and_never_returns_future_bars() -> None:
    source = SequenceProvider([[bar(9), bar(11)], [bar(9)]])
    provider = ResilientMarketDataProvider(
        source,
        policy=policy(attempts=1, max_staleness_days=5),
    )

    first = provider.get_history("AAA", date(2026, 1, 1), date(2026, 1, 10))
    repeated = provider.get_history("AAA", date(2026, 1, 1), date(2026, 1, 10))
    narrower = provider.get_history("AAA", date(2026, 1, 2), date(2026, 1, 10))

    assert [item.timestamp for item in first] == [date(2026, 1, 9)]
    assert repeated == first
    assert source.calls == 2
    assert narrower == [bar(9)]
    provider.close()


class SlowProvider(MarketDataProvider):
    def get_history(self, ticker: str, start_date: date, end_date: date):
        sleep(0.1)
        return [bar(9)]


def test_provider_timeout_is_bounded() -> None:
    provider = ResilientMarketDataProvider(
        SlowProvider(),
        policy=policy(attempts=1, timeout_seconds=0.01),
    )

    with pytest.raises(MarketDataOperationalError):
        provider.get_history("AAA", date(2026, 1, 1), date(2026, 1, 10))
    provider.close()
