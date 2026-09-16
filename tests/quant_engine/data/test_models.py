"""
tests/quant_engine/data/test_models.py
======================================
Tests for market data models.
"""

from datetime import date
import pytest
from pydantic import ValidationError
from quant_engine.data.models import MarketBar


def test_valid_market_bar():
    bar = MarketBar(
        ticker="AAPL",
        timestamp=date(2023, 1, 1),
        open=150.0,
        high=155.0,
        low=149.0,
        close=154.0,
        volume=1000000
    )
    assert bar.ticker == "AAPL"


def test_negative_price():
    with pytest.raises(ValidationError, match="must be > 0"):
        MarketBar(
            ticker="AAPL",
            timestamp=date(2023, 1, 1),
            open=-150.0,
            high=155.0,
            low=149.0,
            close=154.0,
            volume=1000000
        )


def test_negative_volume():
    with pytest.raises(ValidationError, match="must be >= 0"):
        MarketBar(
            ticker="AAPL",
            timestamp=date(2023, 1, 1),
            open=150.0,
            high=155.0,
            low=149.0,
            close=154.0,
            volume=-10
        )


def test_high_less_than_low():
    with pytest.raises(ValidationError, match="cannot be < low"):
        MarketBar(
            ticker="AAPL",
            timestamp=date(2023, 1, 1),
            open=150.0,
            high=148.0,  # High < Low
            low=149.0,
            close=154.0,
            volume=1000000
        )


def test_high_less_than_open():
    with pytest.raises(ValidationError, match="high must be >="):
        MarketBar(
            ticker="AAPL",
            timestamp=date(2023, 1, 1),
            open=160.0,
            high=155.0,  # High < Open
            low=149.0,
            close=154.0,
            volume=1000000
        )
