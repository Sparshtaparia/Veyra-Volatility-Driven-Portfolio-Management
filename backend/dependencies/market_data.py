"""Configured resilient market-data provider dependency."""

from functools import lru_cache

from backend.operations.market_data import ProviderPolicy, ResilientMarketDataProvider
from config.settings import get_settings
from quant_engine.data.provider import (
    AlphaVantageProvider,
    MarketDataProvider,
    YahooChartProvider,
    YFinanceProvider,
)


def _provider(name: str) -> MarketDataProvider | None:
    settings = get_settings()
    if name == "yfinance":
        return YFinanceProvider(settings.market_data_timeout_seconds)
    if name == "alpha_vantage":
        if settings.alpha_vantage_api_key is None:
            return None
        return AlphaVantageProvider(
            settings.alpha_vantage_api_key.get_secret_value(), settings.market_data_timeout_seconds
        )
    if name == "yahoo_chart":
        return YahooChartProvider(settings.market_data_timeout_seconds)
    raise ValueError(f"unsupported market-data provider: {name}")


@lru_cache(maxsize=1)
def get_market_data_provider() -> ResilientMarketDataProvider:
    settings = get_settings()
    secondary_name = settings.market_data_secondary_provider
    tertiary_name = settings.market_data_fallback_provider
    primary = _provider(settings.market_data_provider)
    assert primary is not None
    secondary = _provider(secondary_name) if secondary_name else None
    tertiary = _provider(tertiary_name) if tertiary_name else None
    return ResilientMarketDataProvider(
        primary,
        fallback=secondary,
        tertiary=tertiary,
        primary_name=settings.market_data_provider,
        fallback_name=secondary_name if secondary else None,
        tertiary_name=tertiary_name if tertiary else None,
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
