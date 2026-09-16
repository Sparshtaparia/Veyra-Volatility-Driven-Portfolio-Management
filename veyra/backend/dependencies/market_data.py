"""Market-data provider dependency for application-level evaluation routes."""

from quant_engine.data.provider import MarketDataProvider, YFinanceProvider


def get_market_data_provider() -> MarketDataProvider:
    return YFinanceProvider()
