"""Configured resilient market-data provider dependency."""

from functools import lru_cache

from backend.operations.market_data import ProviderPolicy, ResilientMarketDataProvider
from config.settings import get_settings
from quant_engine.data.provider import (
    MarketDataProvider,
    YahooChartProvider,
    YFinanceProvider,
)


def _provider(name: str) -> MarketDataProvider:
    if name == "yfinance":
        return YFinanceProvider(get_settings().market_data_timeout_seconds)
    if name == "yahoo_chart":
        return YahooChartProvider(get_settings().market_data_timeout_seconds)
    raise ValueError(f"unsupported market-data provider: {name}")


@lru_cache(maxsize=1)
def get_market_data_provider() -> ResilientMarketDataProvider:
    settings = get_settings()
    fallback_name = settings.market_data_fallback_provider
    return ResilientMarketDataProvider(
        _provider(settings.market_data_provider),
        fallback=_provider(fallback_name) if fallback_name else None,
        primary_name=settings.market_data_provider,
        fallback_name=fallback_name,
        policy=ProviderPolicy(
            attempts=settings.market_data_retry_attempts,
            base_backoff_seconds=settings.market_data_backoff_seconds,
            max_backoff_seconds=settings.market_data_max_backoff_seconds,
            timeout_seconds=settings.market_data_timeout_seconds,
            requests_per_second=settings.market_data_requests_per_second,
            max_staleness_days=settings.market_data_max_staleness_days,
            cache_ttl_seconds=settings.market_data_cache_ttl_seconds,
        ),
    )
