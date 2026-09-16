"""
tests/quant_engine/data/test_provider.py
========================================
Tests for data providers.
"""

from datetime import date

from quant_engine.data.models import MarketBar
from quant_engine.data.provider import MockProvider


def test_mock_provider():
    bars = [
        MarketBar(
            ticker="TCS",
            timestamp=date(2024, 1, 1),
            open=100,
            high=110,
            low=90,
            close=105,
            volume=1000,
        ),
        MarketBar(
            ticker="TCS",
            timestamp=date(2024, 1, 2),
            open=105,
            high=115,
            low=100,
            close=110,
            volume=2000,
        ),
        MarketBar(
            ticker="INFY",
            timestamp=date(2024, 1, 1),
            open=50,
            high=55,
            low=45,
            close=52,
            volume=500,
        ),
    ]
    provider = MockProvider(data=bars)

    # Test valid fetch
    results = provider.get_history("TCS", date(2024, 1, 1), date(2024, 1, 2))
    assert len(results) == 2

    # Test out of bounds
    results = provider.get_history("TCS", date(2024, 1, 3), date(2024, 1, 4))
    assert len(results) == 0

    # Test different ticker
    results = provider.get_history("INFY", date(2024, 1, 1), date(2024, 1, 1))
    assert len(results) == 1
    assert results[0].ticker == "INFY"
